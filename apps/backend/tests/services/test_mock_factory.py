import asyncio
import gc
import warnings

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from httpx import ASGITransport, AsyncClient


def _make_factory(*, simulation_speed: float = 1.0, enabled: bool = True) -> MockFactory:
    config = MockFactoryConfig(robot_count=1, simulation_speed=simulation_speed)
    state = FactoryState(config=config)
    return MockFactory(state=state, config=config, enabled=enabled)


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

    async def flaky_tick(dt: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("boom")
        await original_tick(dt)

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
async def test_lifespan_starts_and_stops_engine_without_pending_tasks() -> None:
    transport = ASGITransport(app=app)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        async with app.router.lifespan_context(app):
            mock_factory = app.state.mock_factory
            assert mock_factory.running is True

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200

        assert mock_factory.running is False
        assert mock_factory._task is None

    gc.collect()
    pending_warnings = [w for w in caught if "was destroyed but it is pending" in str(w.message)]
    assert not pending_warnings
