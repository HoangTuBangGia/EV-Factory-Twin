from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.metrics_service import (
    STARVATION_THRESHOLD_SECONDS,
    MetricsService,
    RuntimeMetricsPublisher,
)
from ev_twin_api.services.websocket_manager import WebSocketManager


def _new_state(robot_count: int = 1) -> FactoryState:
    return FactoryState(config=MockFactoryConfig(robot_count=robot_count))


def _task(
    task_id: str,
    status: TaskStatus,
    *,
    created_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> Task:
    return Task(
        task_id=task_id,
        payload_id=f"BP-{task_id}",
        pickup="BATTERY_BUFFER",
        dropoff="MARRIAGE_STATION",
        status=status,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=completed_at,
    )


def _completed_task(task_id: str, cycle_seconds: float) -> Task:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    return _task(
        task_id,
        TaskStatus.COMPLETED,
        created_at=created,
        completed_at=created + timedelta(seconds=cycle_seconds),
    )


def test_throughput_from_guide_example() -> None:
    state = _new_state()
    state.add_task(_completed_task("TASK-0001", 10))
    state.add_task(_completed_task("TASK-0002", 20))
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=120.0)

    assert metrics.completed_tasks == 2
    assert metrics.throughput_per_hour == pytest.approx(60.0)


def test_average_cycle_time_from_guide_example() -> None:
    state = _new_state()
    state.add_task(_completed_task("TASK-0001", 40))
    state.add_task(_completed_task("TASK-0002", 60))
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=100.0)

    assert metrics.average_cycle_time_seconds == pytest.approx(50.0)


def test_elapsed_zero_does_not_raise_and_throughput_is_zero() -> None:
    state = _new_state()
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=0.0)

    assert metrics.throughput_per_hour == 0.0
    assert metrics.completed_tasks == 0


def test_no_completed_tasks_gives_zero_average_cycle_time() -> None:
    state = _new_state()
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=100.0)

    assert metrics.average_cycle_time_seconds == 0.0


def test_active_and_queued_tasks_counted_correctly() -> None:
    state = _new_state()
    state.add_task(_task("TASK-0001", TaskStatus.QUEUED))
    state.add_task(_task("TASK-0002", TaskStatus.ASSIGNED))
    state.add_task(_task("TASK-0003", TaskStatus.PICKUP))
    state.add_task(_task("TASK-0004", TaskStatus.IN_PROGRESS))
    state.add_task(_task("TASK-0005", TaskStatus.DELIVERED))
    state.add_task(_task("TASK-0006", TaskStatus.COMPLETED))
    state.add_task(_task("TASK-0007", TaskStatus.FAILED))
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=100.0)

    assert metrics.queued_tasks == 1
    assert metrics.active_tasks == 4


def test_fleet_utilization_counts_only_the_four_productive_statuses() -> None:
    state = _new_state(robot_count=5)
    statuses = [
        RobotStatus.MOVING_TO_PICKUP,
        RobotStatus.PICKING,
        RobotStatus.IDLE,
        RobotStatus.CHARGING,
        RobotStatus.MOVING_TO_CHARGER,
    ]
    for robot_id, status in zip((f"AMR-{i:02d}" for i in range(1, 6)), statuses, strict=True):
        robot = state.get_robot(robot_id)
        assert robot is not None
        robot.status = status
        state.update_robot(robot)
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=100.0)

    assert metrics.fleet_utilization_percent == pytest.approx(40.0)  # 2 of 5 productive


def test_starvation_is_not_double_counted_for_the_same_task() -> None:
    state = _new_state()
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    state.add_task(
        _task("TASK-0001", TaskStatus.QUEUED, created_at=datetime(1970, 1, 1, tzinfo=UTC))
    )
    service = MetricsService(state, clock=lambda: now[0])

    first = service.recalculate(simulated_elapsed_seconds=100.0)
    now[0] += timedelta(seconds=STARVATION_THRESHOLD_SECONDS + 1)
    second = service.recalculate(simulated_elapsed_seconds=101.0)
    third = service.recalculate(simulated_elapsed_seconds=102.0)

    assert first.starvation_events == 0
    assert second.starvation_events == 1
    assert third.starvation_events == 1


def test_starvation_does_not_trigger_before_threshold() -> None:
    state = _new_state()
    state.add_task(_task("TASK-0001", TaskStatus.QUEUED, created_at=datetime.now(UTC)))
    service = MetricsService(state)

    metrics = service.recalculate(simulated_elapsed_seconds=100.0)

    assert metrics.starvation_events == 0


def test_starvation_counts_a_second_distinct_starved_task() -> None:
    state = _new_state()
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    source_epoch = datetime(1970, 1, 1, tzinfo=UTC)
    state.add_task(_task("TASK-0001", TaskStatus.QUEUED, created_at=source_epoch))
    service = MetricsService(state, clock=lambda: now[0])
    service.recalculate(simulated_elapsed_seconds=100.0)
    now[0] += timedelta(seconds=STARVATION_THRESHOLD_SECONDS + 1)
    service.recalculate(simulated_elapsed_seconds=101.0)

    state.add_task(_task("TASK-0002", TaskStatus.QUEUED, created_at=source_epoch))
    service.recalculate(simulated_elapsed_seconds=102.0)
    now[0] += timedelta(seconds=STARVATION_THRESHOLD_SECONDS + 1)
    metrics = service.recalculate(simulated_elapsed_seconds=103.0)

    assert metrics.starvation_events == 2


def test_reset_clears_the_starvation_counter() -> None:
    state = _new_state()
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    state.add_task(_task("TASK-0001", TaskStatus.QUEUED))
    service = MetricsService(state, clock=lambda: now[0])
    service.recalculate(simulated_elapsed_seconds=100.0)
    now[0] += timedelta(seconds=STARVATION_THRESHOLD_SECONDS + 1)
    service.recalculate(simulated_elapsed_seconds=101.0)

    service.reset()
    state.reset()
    metrics = service.recalculate(simulated_elapsed_seconds=0.0)

    assert metrics.starvation_events == 0


@pytest.mark.asyncio
async def test_live_metrics_refresh_is_throttled_and_broadcasts_authoritative_state() -> None:
    state = _new_state()
    state.add_task(_completed_task("TASK-0001", 10))
    manager = WebSocketManager()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    current = 60.0
    publisher = RuntimeMetricsPublisher(
        state,
        manager,
        enabled=True,
        interval_seconds=1,
        monotonic=lambda: current,
    )

    assert await publisher.refresh()
    assert not await publisher.refresh()
    assert state.get_metrics().completed_tasks == 1
    manager.broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_metrics_publisher_is_inert_for_mock_runtime() -> None:
    state = _new_state()
    manager = WebSocketManager()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    publisher = RuntimeMetricsPublisher(state, manager, enabled=False)

    assert not await publisher.refresh(force=True)
    manager.broadcast.assert_not_awaited()
