from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.edge_runtime import BridgeHealth, TaskUpdate
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.task import TaskStatus
from ev_twin_api.services.edge_runtime import EdgeRuntimeService
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.websocket_manager import WebSocketManager


def make_service() -> tuple[EdgeRuntimeService, FactoryState, WebSocketManager]:
    state = FactoryState(MockFactoryConfig(), seed_mock_robots=False)
    manager = WebSocketManager()
    return EdgeRuntimeService(state, manager), state, manager


def task_update(timestamp: datetime, status: TaskStatus = TaskStatus.QUEUED) -> TaskUpdate:
    return TaskUpdate(
        task_id="TASK-0001",
        payload_id="BP-0001",
        pickup_station_id="BATTERY_BUFFER",
        dropoff_station_id="MARRIAGE_STATION",
        assigned_robot_id="AMR-01" if status != TaskStatus.QUEUED else None,
        status=status,
        attempt=1,
        max_retries=1,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_task_update_changes_snapshot_and_broadcasts() -> None:
    service, state, manager = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    now = datetime.now(UTC)

    result = await service.ingest_task(task_update(now, TaskStatus.ASSIGNED))

    assert result.accepted
    task = state.get_task("TASK-0001")
    assert task is not None
    assert task.status == TaskStatus.ASSIGNED
    assert task.assigned_robot_id == "AMR-01"
    manager.broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_stale_task_update_is_ignored() -> None:
    service, state, manager = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    now = datetime.now(UTC)
    await service.ingest_task(task_update(now, TaskStatus.ASSIGNED))
    manager.broadcast.reset_mock()

    result = await service.ingest_task(task_update(now - timedelta(seconds=1), TaskStatus.QUEUED))

    assert not result.accepted
    assert state.get_task("TASK-0001").status == TaskStatus.ASSIGNED
    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_health_keeps_latest_timestamp() -> None:
    service, state, manager = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    now = datetime.now(UTC)
    health = BridgeHealth(
        bridge_id="edge-main",
        status="CONNECTED",
        robot_ids=["AMR-01", "AMR-02"],
        timestamp=now,
        delivered_samples=2,
        failed_deliveries=0,
    )
    assert (await service.ingest_health(health)).accepted
    assert {robot.id for robot in state.list_robots()} == {"AMR-01", "AMR-02"}
    manager.broadcast.assert_awaited_once_with({"type": "factory.reset", "data": None})
    manager.broadcast.reset_mock()
    assert not (
        await service.ingest_health(
            health.model_copy(update={"timestamp": now - timedelta(seconds=1)})
        )
    ).accepted
    assert service.get_health("edge-main") == health
    assert {robot.id for robot in state.list_robots()} == {"AMR-01", "AMR-02"}
    manager.broadcast.assert_not_awaited()


def test_bridge_health_rejects_duplicate_robot_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        BridgeHealth(
            bridge_id="edge-main",
            status="CONNECTED",
            robot_ids=["AMR-01", "AMR-01"],
            timestamp=datetime.now(UTC),
            delivered_samples=0,
            failed_deliveries=0,
        )
