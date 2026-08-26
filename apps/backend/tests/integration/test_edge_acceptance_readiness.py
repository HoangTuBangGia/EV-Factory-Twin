from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.edge_runtime import BridgeHealth, BridgeStatus, TaskUpdate
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import Pose, RobotStatus, Velocity
from ev_twin_api.schemas.task import TaskStatus
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.edge_runtime import EdgeRuntimeService
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.telemetry_ingress import TelemetryIngressService
from ev_twin_api.services.websocket_manager import WebSocketManager


def telemetry(robot_id: str, timestamp: datetime, x: float) -> RobotTelemetry:
    return RobotTelemetry(
        robot_id=robot_id,
        timestamp=timestamp,
        pose=Pose(x=x, y=2, yaw=0),
        velocity=Velocity(linear=1, angular=0),
        battery=80,
        status=RobotStatus.MOVING,
        task_id="TASK-EDGE-01" if robot_id == "AMR-01" else None,
        payload_id="BP-EDGE-01" if robot_id == "AMR-01" else None,
    )


@pytest.mark.asyncio
async def test_two_robot_edge_flow_preserves_isolation_ordering_and_task_state() -> None:
    config = MockFactoryConfig()
    state = FactoryState(config, seed_mock_robots=False)
    manager = WebSocketManager()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    mock_factory = MockFactory(state, config, manager, enabled=False)
    edge = EdgeRuntimeService(state, manager)
    ingress = TelemetryIngressService(state, manager, mock_factory, max_future_skew_seconds=5)
    now = datetime.now(UTC)

    registered = await edge.ingest_health(
        BridgeHealth(
            bridge_id="edge-main",
            status=BridgeStatus.CONNECTED,
            robot_ids=["AMR-01", "AMR-02"],
            timestamp=now,
            delivered_samples=0,
            failed_deliveries=0,
        )
    )
    amr_01 = await ingress.ingest(telemetry("AMR-01", now + timedelta(seconds=1), 10))
    amr_02 = await ingress.ingest(telemetry("AMR-02", now + timedelta(seconds=1), 20))
    stale = await ingress.ingest(telemetry("AMR-01", now, 999))
    task = await edge.ingest_task(
        TaskUpdate(
            task_id="TASK-EDGE-01",
            payload_id="BP-EDGE-01",
            pickup_station_id="BATTERY_BUFFER",
            dropoff_station_id="MARRIAGE_STATION",
            assigned_robot_id="AMR-01",
            status=TaskStatus.DELIVERING,
            attempt=1,
            max_retries=1,
            updated_at=now + timedelta(seconds=1),
        )
    )

    assert registered.accepted
    assert amr_01.status == amr_02.status == TelemetryIngressStatus.ACCEPTED
    assert stale.status == TelemetryIngressStatus.IGNORED_STALE
    assert task.accepted
    robot_01 = state.get_robot("AMR-01")
    robot_02 = state.get_robot("AMR-02")
    current_task = state.get_task("TASK-EDGE-01")
    assert robot_01 is not None
    assert robot_02 is not None
    assert current_task is not None
    assert robot_01.pose.x == 10
    assert robot_02.pose.x == 20
    assert current_task.status == TaskStatus.DELIVERING
    event_types = [call.args[0]["type"] for call in manager.broadcast.await_args_list]
    assert event_types == [
        "factory.reset",
        "robot.telemetry",
        "robot.telemetry",
        "task.updated",
    ]
