import json
from datetime import UTC, datetime
from pathlib import Path
from time import time
from uuid import UUID

import ev_twin_api.main as main_module
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.api.websocket import get_websocket_auth_service
from ev_twin_api.core.config import Settings, get_settings
from ev_twin_api.core.security import InvalidAccessTokenError
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from ev_twin_api.schemas.robot import Robot
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.services.auth_service import AuthenticatedSession
from fastapi.testclient import TestClient

EDGE_SECRET = "integration-edge-secret-000000000000"
ORIGIN = "http://localhost:3000"
USER = CurrentUser(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    email="monitor@example.com",
    display_name="Integration Monitor",
    role=AppRole.MONITOR,
    is_active=True,
)


class StaticAuthService:
    async def authenticate(self, token: str | None) -> AuthenticatedSession:
        if token != "integration-token":
            raise InvalidAccessTokenError("invalid token")
        return AuthenticatedSession(user=USER, expires_at=int(time()) + 60)


def test_edge_telemetry_reaches_authenticated_websocket_and_rest_state() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins=[ORIGIN],
        edge_telemetry_shared_secret=EDGE_SECRET,
        mock_factory_enabled=False,
    )
    previous_settings = main_module.settings
    previous_overrides = app.dependency_overrides.copy()
    previous_state = app.state._state.copy()
    app.dependency_overrides.update(
        {
            get_settings: lambda: settings,
            get_current_user: lambda: USER,
            get_websocket_auth_service: lambda: StaticAuthService(),
        }
    )
    main_module.settings = settings

    try:
        with TestClient(app) as client:
            fixture = (
                Path(__file__).parents[2]
                / "ros2_ws/src/telemetry_bridge/test/fixtures/robot_telemetry.json"
            )
            payload = json.loads(fixture.read_text())
            payload["timestamp"] = datetime.now(UTC).isoformat()
            telemetry = RobotTelemetry.model_validate(payload)

            with client.websocket_connect("/ws/factory", headers={"origin": ORIGIN}) as websocket:
                websocket.send_json({"type": "auth", "access_token": "integration-token"})
                assert websocket.receive_json()["type"] == "auth.ok"

                accepted = client.post(
                    "/internal/v1/telemetry",
                    json=payload,
                    headers={"Authorization": f"Bearer {EDGE_SECRET}"},
                )
                event = websocket.receive_json()

                task_timestamp = datetime.now(UTC).isoformat()
                task_accepted = client.post(
                    "/internal/v1/task-updates",
                    json={
                        "task_id": "TASK-EDGE-0001",
                        "payload_id": "BP-EDGE-0001",
                        "pickup_station_id": "BATTERY_BUFFER",
                        "dropoff_station_id": "MARRIAGE_STATION",
                        "assigned_robot_id": "AMR-01",
                        "status": "ASSIGNED",
                        "attempt": 1,
                        "max_retries": 1,
                        "message": "robot assigned",
                        "updated_at": task_timestamp,
                    },
                    headers={"Authorization": f"Bearer {EDGE_SECRET}"},
                )
                task_event = websocket.receive_json()
                health_accepted = client.post(
                    "/internal/v1/bridge-health",
                    json={
                        "bridge_id": "edge-main",
                        "status": "CONNECTED",
                        "robot_ids": ["AMR-01", "AMR-02"],
                        "timestamp": datetime.now(UTC).isoformat(),
                        "delivered_samples": 2,
                        "failed_deliveries": 0,
                        "last_error": None,
                    },
                    headers={"Authorization": f"Bearer {EDGE_SECRET}"},
                )

            assert accepted.status_code == 200
            assert accepted.json()["status"] == "ACCEPTED"
            assert event == {
                "type": "robot.telemetry",
                "data": telemetry.model_dump(mode="json"),
            }
            assert task_accepted.status_code == 200
            assert task_accepted.json()["accepted"] is True
            assert task_event["type"] == "task.updated"
            assert task_event["data"]["task_id"] == "TASK-EDGE-0001"
            assert health_accepted.status_code == 200
            assert health_accepted.json()["accepted"] is True

            task_response = client.get("/api/v1/tasks/TASK-EDGE-0001")
            assert task_response.status_code == 200
            assert task_response.json()["status"] == "ASSIGNED"

            state_response = client.get("/api/v1/robots/AMR-01")
            assert state_response.status_code == 200
            robot = Robot.model_validate(state_response.json())
            assert robot.pose == telemetry.pose
            assert robot.velocity == telemetry.velocity
            assert robot.battery == telemetry.battery
            assert robot.status == telemetry.status
            assert robot.task_id == telemetry.task_id
            assert robot.payload_id == telemetry.payload_id
            assert robot.last_seen_at == datetime.fromisoformat(
                telemetry.model_dump(mode="json")["timestamp"].replace("Z", "+00:00")
            )
    finally:
        main_module.settings = previous_settings
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        app.state._state.clear()
        app.state._state.update(previous_state)
