from unittest.mock import AsyncMock

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.mock import MockControlResponse
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_config_with_invalid_body_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/mock/config", json={"robot_count": 0})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_config_updates_and_echoes_applied_values(client: AsyncClient) -> None:
    payload = {
        "robot_count": 3,
        "task_interval_seconds": 15.0,
        "robot_speed_mps": 2.0,
        "simulation_speed": 5.0,
        "low_battery_threshold": 25.0,
    }

    response = await client.post("/api/v1/mock/config", json=payload)

    assert response.status_code == 200
    config = MockFactoryConfig.model_validate(response.json())
    assert config.robot_count == 3
    assert config.task_interval_seconds == 15.0
    assert config.robot_speed_mps == 2.0
    assert config.simulation_speed == 5.0
    assert config.low_battery_threshold == 25.0

    # the shared config object is mutated in place, so the live engine sees it too
    assert app.state.mock_factory.config.task_interval_seconds == 15.0
    assert app.state.factory_state.config.task_interval_seconds == 15.0


@pytest.mark.asyncio
async def test_stop_sets_running_state_false(client: AsyncClient) -> None:
    stop_response = await client.post("/api/v1/mock/stop")
    assert stop_response.status_code == 200
    stopped = MockControlResponse.model_validate(stop_response.json())
    assert stopped.running is False


@pytest.mark.asyncio
async def test_start_is_idempotent_and_reports_running(client: AsyncClient) -> None:
    start_response = await client.post("/api/v1/mock/start")
    assert start_response.status_code == 200
    started = MockControlResponse.model_validate(start_response.json())
    assert started.running is True


@pytest.mark.asyncio
async def test_reset_restores_initial_state(client: AsyncClient) -> None:
    factory_state = app.state.factory_state
    robot = factory_state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 5.0
    factory_state.update_robot(robot)
    app.state.mock_factory._task_service.generate_task()
    assert factory_state.list_tasks() != []

    response = await client.post("/api/v1/mock/reset")

    assert response.status_code == 200
    result = MockControlResponse.model_validate(response.json())
    assert result.tick_count == 0
    assert result.simulated_elapsed_seconds == 0.0

    restored_robot = factory_state.get_robot("AMR-01")
    assert restored_robot is not None
    assert restored_robot.battery == 100.0
    assert factory_state.list_tasks() == []


@pytest.mark.asyncio
async def test_reset_broadcasts_factory_reset_event(client: AsyncClient) -> None:
    broadcast = AsyncMock()
    app.state.websocket_manager.broadcast = broadcast

    response = await client.post("/api/v1/mock/reset")

    assert response.status_code == 200
    assert any(
        call.args[0] == {"type": "factory.reset", "data": None}
        for call in broadcast.await_args_list
    )
