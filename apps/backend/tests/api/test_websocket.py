from ev_twin_api.main import app
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.schemas.websocket import WebSocketEvent
from fastapi.testclient import TestClient


def test_client_connects_and_receives_robot_telemetry() -> None:
    with TestClient(app) as client, client.websocket_connect("/ws/factory") as websocket:
        message = websocket.receive_json()

    event = WebSocketEvent.model_validate(message)
    assert event.type == "robot.telemetry"
    telemetry = RobotTelemetry.model_validate(message["data"])
    assert telemetry.robot_id.startswith("AMR-")


def test_client_receives_changing_amr_coordinates_without_polling() -> None:
    # acceptance criterion (guide BE-6): "A test/client receives changing AMR
    # coordinates without polling." Speed up one robot so its pose visibly
    # changes across a handful of telemetry messages within the test window.
    with TestClient(app) as client:
        app.state.mock_factory.config.task_interval_seconds = 1.0
        app.state.mock_factory.config.simulation_speed = 10.0
        app.state.mock_factory.config.robot_speed_mps = 3.0

        with client.websocket_connect("/ws/factory") as websocket:
            positions: list[tuple[float, float]] = []
            for _ in range(500):
                message = websocket.receive_json()
                if message["type"] != "robot.telemetry":
                    continue
                telemetry = RobotTelemetry.model_validate(message["data"])
                if telemetry.robot_id != "AMR-01":
                    continue
                positions.append((telemetry.pose.x, telemetry.pose.y))
                if len(positions) >= 2 and positions[-1] != positions[0]:
                    break

    assert len(positions) >= 2
    assert positions[-1] != positions[0]


def test_multiple_clients_receive_the_same_broadcast() -> None:
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws/factory") as ws1,
        client.websocket_connect("/ws/factory") as ws2,
    ):
        msg1 = ws1.receive_json()
        msg2 = ws2.receive_json()

    assert msg1["type"] == "robot.telemetry"
    assert msg2["type"] == "robot.telemetry"


def test_client_disconnect_does_not_crash_subsequent_connections() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/factory") as websocket:
            websocket.receive_json()
        # websocket above disconnected on context exit; app must still be healthy
        with client.websocket_connect("/ws/factory") as websocket2:
            message = websocket2.receive_json()

        response = client.get("/health")

    assert message["type"] == "robot.telemetry"
    assert response.status_code == 200


def test_task_updated_event_is_broadcast() -> None:
    with TestClient(app) as client:
        app.state.mock_factory.config.task_interval_seconds = 1.0
        app.state.mock_factory.config.simulation_speed = 10.0

        with client.websocket_connect("/ws/factory") as websocket:
            task_seen = False
            for _ in range(500):
                message = websocket.receive_json()
                if message["type"] == "task.updated":
                    task_seen = True
                    Task.model_validate(message["data"])
                    break

    assert task_seen
