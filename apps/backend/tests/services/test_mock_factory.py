import asyncio
import gc
import warnings
from typing import Any
from uuid import UUID

import pytest
from ev_twin_api.core.layout import FACTORY_HEIGHT_M, FACTORY_WIDTH_M
from ev_twin_api.main import app
from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.services.battery_service import CHARGE_TARGET_PERCENT
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.websocket_manager import WebSocketManager
from httpx2 import ASGITransport, AsyncClient

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


def _make_factory(
    *,
    simulation_speed: float = 1.0,
    enabled: bool = True,
    task_interval_seconds: float = 8.0,
    robot_speed_mps: float = 1.2,
    websocket_manager: WebSocketManager | None = None,
) -> MockFactory:
    config = MockFactoryConfig(
        robot_count=1,
        simulation_speed=simulation_speed,
        task_interval_seconds=task_interval_seconds,
        robot_speed_mps=robot_speed_mps,
    )
    state = FactoryState(config=config)
    return MockFactory(
        state=state,
        config=config,
        websocket_manager=websocket_manager or WebSocketManager(),
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_tick_count_increases_while_running() -> None:
    factory = _make_factory()
    await factory.start()
    try:
        await asyncio.sleep(0.5)
        assert factory.tick_count >= 4
    finally:
        await factory.stop()


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    factory = _make_factory()
    await factory.start()
    task_after_first_start = factory._task
    await factory.start()
    try:
        assert factory._task is task_after_first_start
    finally:
        await factory.stop()


@pytest.mark.asyncio
async def test_stop_halts_tick_progress() -> None:
    factory = _make_factory()
    await factory.start()
    await asyncio.sleep(0.3)
    await factory.stop()
    count_after_stop = factory.tick_count

    await asyncio.sleep(0.3)
    assert factory.tick_count == count_after_stop


@pytest.mark.asyncio
async def test_stop_leaves_no_pending_task() -> None:
    factory = _make_factory()
    await factory.start()
    task = factory._task
    assert task is not None

    await factory.stop()

    assert factory._task is None
    assert task.done()


@pytest.mark.asyncio
async def test_stop_without_start_does_not_raise() -> None:
    factory = _make_factory()
    await factory.stop()


@pytest.mark.asyncio
async def test_tick_exception_does_not_kill_the_loop() -> None:
    factory = _make_factory()
    call_count = 0
    original_tick = factory.tick

    async def flaky_tick(dt: float, *, wall_dt: float | None = None) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("boom")
        await original_tick(dt, wall_dt=wall_dt)

    factory.tick = flaky_tick  # type: ignore[method-assign]

    await factory.start()
    try:
        await asyncio.sleep(0.5)
        assert call_count > 2
        assert factory.running is True
    finally:
        await factory.stop()


@pytest.mark.asyncio
async def test_disabled_factory_does_not_start_loop() -> None:
    factory = _make_factory(enabled=False)
    await factory.start()
    await asyncio.sleep(0.2)

    assert factory.tick_count == 0
    assert factory._task is None


@pytest.mark.asyncio
async def test_simulation_speed_scales_simulated_elapsed_time() -> None:
    factory_normal = _make_factory(simulation_speed=1.0)
    factory_fast = _make_factory(simulation_speed=2.0)

    await factory_normal.start()
    await factory_fast.start()
    try:
        await asyncio.sleep(0.5)
    finally:
        await factory_normal.stop()
        await factory_fast.stop()

    assert factory_normal.simulated_elapsed_seconds > 0
    ratio = factory_fast.simulated_elapsed_seconds / factory_normal.simulated_elapsed_seconds
    assert 1.5 <= ratio <= 2.5


@pytest.mark.asyncio
async def test_reset_zeroes_counters_and_restores_state() -> None:
    factory = _make_factory()
    await factory.start()
    await asyncio.sleep(0.3)
    assert factory.tick_count > 0

    robot = factory._state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 5.0
    factory._state.update_robot(robot)

    await factory.reset()

    assert factory.tick_count == 0
    assert factory.simulated_elapsed_seconds == 0.0
    restored_robot = factory._state.get_robot("AMR-01")
    assert restored_robot is not None
    assert restored_robot.battery == 100.0
    assert factory.running is True

    await factory.stop()


@pytest.mark.asyncio
async def test_assigned_robot_moves_deterministically_through_the_factory() -> None:
    factory = _make_factory()
    factory.assign_route("AMR-01", ("BATTERY_BUFFER", "MARRIAGE_STATION"))
    # tick() only advances movement for robots in a moving status (BE-006b); a raw
    # assign_route() alone (bypassing the task state machine) needs this too.
    robot = factory._state.get_robot("AMR-01")
    assert robot is not None
    robot.status = RobotStatus.MOVING_TO_PICKUP
    factory._state.update_robot(robot)

    initial = factory._state.get_robot("AMR-01")
    assert initial is not None

    await factory.start()
    try:
        await asyncio.sleep(0.5)
    finally:
        await factory.stop()

    moved = factory._state.get_robot("AMR-01")
    assert moved is not None
    assert (moved.pose.x, moved.pose.y) != (initial.pose.x, initial.pose.y)
    assert 0 <= moved.pose.x <= FACTORY_WIDTH_M
    assert 0 <= moved.pose.y <= FACTORY_HEIGHT_M


@pytest.mark.asyncio
async def test_tasks_are_generated_on_the_configured_simulated_interval() -> None:
    # task_interval_seconds=1.0 (schema minimum) combined with simulation_speed=10.0
    # (schema maximum) means 1 simulated second elapses per real tick, so a handful
    # of real ticks is enough to observe several generations without a long sleep.
    factory = _make_factory(task_interval_seconds=1.0, simulation_speed=10.0)
    # keep this test isolated to generation cadence: make the only robot ineligible
    # for assignment (BE-006b) so every generated task stays QUEUED.
    robot = factory._state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 0.0
    factory._state.update_robot(robot)

    await factory.start()
    try:
        await asyncio.sleep(0.35)
    finally:
        await factory.stop()

    tasks = factory._state.list_tasks()
    assert len(tasks) >= 2
    for task in tasks:
        assert task.status == "QUEUED"


@pytest.mark.asyncio
async def test_robot_state_machine_progresses_through_full_task_cycle() -> None:
    # deterministic, no real-time sleep: drive tick() directly with a fixed dt.
    # task_interval_seconds is schema-maxed (60s) and the loop stays well under
    # that in simulated time, so auto-generation never produces a second task
    # to interfere with observing this one robot's full cycle.
    factory = _make_factory(task_interval_seconds=60.0, robot_speed_mps=3.0)
    factory._task_service.generate_task()

    seen_statuses: list[str] = []
    for _ in range(200):
        await factory.tick(0.1)
        robot = factory._state.get_robot("AMR-01")
        assert robot is not None
        if not seen_statuses or seen_statuses[-1] != robot.status:
            seen_statuses.append(robot.status)
        if robot.status == RobotStatus.IDLE and robot.task_id is None and len(seen_statuses) > 1:
            break

    assert seen_statuses == [
        RobotStatus.MOVING_TO_PICKUP,
        RobotStatus.PICKING,
        RobotStatus.DELIVERING,
        RobotStatus.DROPPING,
        RobotStatus.IDLE,
    ]

    task = factory._state.list_tasks()[0]
    assert task.status == "COMPLETED"
    assert task.completed_at is not None
    assert task.assigned_robot_id == "AMR-01"

    final_robot = factory._state.get_robot("AMR-01")
    assert final_robot is not None
    assert final_robot.payload_id is None


@pytest.mark.asyncio
async def test_task_completes_end_to_end_through_the_real_engine_loop() -> None:
    # acceptance criterion (guide BE-5): "A battery delivery task completes
    # end-to-end and the AMR returns to IDLE" — exercised through start()/stop(),
    # not direct tick() calls, so this covers the real asyncio loop too. With a
    # single robot and ongoing task generation, the robot may already be onto a
    # new task by the time we check (correct behavior) — the precise "ends at
    # IDLE" check lives in the deterministic tick()-driven test above, so here
    # we confirm the first task itself reached COMPLETED with the AMR that ran it.
    factory = _make_factory(task_interval_seconds=1.0, simulation_speed=10.0, robot_speed_mps=3.0)

    await factory.start()
    try:
        await asyncio.sleep(2.0)
    finally:
        await factory.stop()

    task_1 = factory._state.get_task("TASK-0001")
    assert task_1 is not None
    assert task_1.status == "COMPLETED"
    assert task_1.assigned_robot_id == "AMR-01"
    assert task_1.completed_at is not None


@pytest.mark.asyncio
async def test_tick_broadcasts_robot_telemetry_matching_schema() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, TEST_USER_ID)  # type: ignore[arg-type]
    factory = _make_factory(websocket_manager=manager)

    await factory.tick(0.1)

    telemetry_events = [msg for msg in websocket.sent if msg["type"] == "robot.telemetry"]
    assert len(telemetry_events) == 1
    telemetry = RobotTelemetry.model_validate(telemetry_events[0]["data"])
    assert telemetry.robot_id == "AMR-01"


@pytest.mark.asyncio
async def test_tick_broadcasts_task_updated_on_assignment() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, TEST_USER_ID)  # type: ignore[arg-type]
    factory = _make_factory(task_interval_seconds=60.0, websocket_manager=manager)
    factory._task_service.generate_task()  # bypasses tick()'s broadcast, nothing sent yet

    await factory.tick(0.1)

    task_updated_events = [msg for msg in websocket.sent if msg["type"] == "task.updated"]
    assert len(task_updated_events) == 1
    task = Task.model_validate(task_updated_events[0]["data"])
    assert task.status == "ASSIGNED"
    assert task.assigned_robot_id == "AMR-01"


@pytest.mark.asyncio
async def test_reset_broadcasts_factory_reset() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, TEST_USER_ID)  # type: ignore[arg-type]
    factory = _make_factory(websocket_manager=manager)

    await factory.reset()

    reset_events = [msg for msg in websocket.sent if msg["type"] == "factory.reset"]
    assert len(reset_events) == 1
    assert reset_events[0]["data"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("simulation_speed", [0.25, 1.0, 10.0])
async def test_metrics_updated_is_broadcast_at_one_hertz_of_wall_time(
    simulation_speed: float,
) -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, TEST_USER_ID)  # type: ignore[arg-type]
    factory = _make_factory(
        task_interval_seconds=60.0,
        simulation_speed=simulation_speed,
        websocket_manager=manager,
    )

    await factory.tick(0.9 * simulation_speed, wall_dt=0.9)
    assert not [msg for msg in websocket.sent if msg["type"] == "metrics.updated"]

    await factory.tick(0.2 * simulation_speed, wall_dt=0.2)
    metrics_events = [msg for msg in websocket.sent if msg["type"] == "metrics.updated"]
    assert len(metrics_events) == 1
    FactoryMetrics.model_validate(metrics_events[0]["data"])


@pytest.mark.asyncio
async def test_low_battery_robot_charges_and_returns_to_idle() -> None:
    # deterministic, no real-time sleep: drive tick() directly with a fixed dt,
    # matching the state-machine test style used for the task delivery cycle.
    factory = _make_factory(task_interval_seconds=60.0, robot_speed_mps=3.0)
    robot = factory._state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 15.0
    factory._state.update_robot(robot)

    seen_statuses: list[str] = []
    for _ in range(500):
        await factory.tick(0.5)
        robot = factory._state.get_robot("AMR-01")
        assert robot is not None
        if not seen_statuses or seen_statuses[-1] != robot.status:
            seen_statuses.append(robot.status)
        if robot.status == RobotStatus.IDLE and len(seen_statuses) > 1:
            break

    assert seen_statuses == [
        RobotStatus.MOVING_TO_CHARGER,
        RobotStatus.CHARGING,
        RobotStatus.IDLE,
    ]

    final_robot = factory._state.get_robot("AMR-01")
    assert final_robot is not None
    assert final_robot.battery >= CHARGE_TARGET_PERCENT
    assert final_robot.pose.x == 2.0
    assert final_robot.pose.y == 12.0


@pytest.mark.asyncio
async def test_metrics_reflect_a_completed_task_through_the_real_engine() -> None:
    # deterministic, no real-time sleep: drive tick() directly with a fixed dt.
    factory = _make_factory(task_interval_seconds=60.0, robot_speed_mps=3.0)
    factory._task_service.generate_task()

    for _ in range(200):
        await factory.tick(0.1)
        task = factory._state.get_task("TASK-0001")
        assert task is not None
        if task.status == "COMPLETED":
            break

    metrics = factory._state.get_metrics()
    assert metrics.completed_tasks == 1
    assert metrics.queued_tasks == 0
    assert metrics.average_cycle_time_seconds > 0
    assert metrics.throughput_per_hour > 0


@pytest.mark.asyncio
async def test_low_battery_alert_is_broadcast_and_deduplicated() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, TEST_USER_ID)  # type: ignore[arg-type]
    factory = _make_factory(task_interval_seconds=60.0, websocket_manager=manager)
    robot = factory._state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 15.0
    factory._state.update_robot(robot)

    await factory.tick(0.1)
    await factory.tick(0.1)
    await factory.tick(0.1)

    alert_events = [msg for msg in websocket.sent if msg["type"] == "alert.created"]
    assert len(alert_events) == 1
    alert = FactoryAlert.model_validate(alert_events[0]["data"])
    assert alert.code == "LOW_BATTERY"
    assert alert.robot_id == "AMR-01"

    stored_alerts = factory._state.list_alerts()
    assert len(stored_alerts) == 1


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_engine_without_pending_tasks() -> None:
    transport = ASGITransport(app=app)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        async with app.router.lifespan_context(app):
            mock_factory = app.state.mock_factory
            assert mock_factory.running is True
            assert app.state.kpi_snapshot_writer is None

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200

        assert mock_factory.running is False
        assert mock_factory._task is None

    gc.collect()
    pending_warnings = [w for w in caught if "was destroyed but it is pending" in str(w.message)]
    assert not pending_warnings
