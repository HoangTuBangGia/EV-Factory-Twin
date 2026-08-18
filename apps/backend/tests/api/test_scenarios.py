from unittest.mock import AsyncMock

import pytest
from conftest import make_test_user
from ev_twin_api.api.scenarios import (
    apply_scenario,
    approve_scenario,
    get_baseline,
    get_scenario,
    list_scenarios,
    reject_scenario,
    run_scenario,
)
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import ScenarioRunRequest, ScenarioStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_service import InvalidScenarioTransitionError, ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager
from fastapi import HTTPException
from pydantic import ValidationError

SCENARIO_PAYLOAD = {
    "name": "candidate-01",
    "num_robots": 3,
    "num_tasks": 10,
    "task_arrival_interval": 10.0,
    "travel_time": 30.0,
    "loading_time": 10.0,
    "simulation_time": 3600.0,
}

DESIGNER = make_test_user(AppRole.DESIGNER)
MONITOR = make_test_user(AppRole.MONITOR)


def build_scenario_service() -> tuple[ScenarioService, MockFactory, FactoryState, WebSocketManager]:
    config = MockFactoryConfig()
    manager = WebSocketManager()
    state = FactoryState(config)
    mock_factory = MockFactory(state, config, manager)
    return ScenarioService(mock_factory), mock_factory, state, manager


def scenario_request(**updates: object) -> ScenarioRunRequest:
    return ScenarioRunRequest.model_validate({**SCENARIO_PAYLOAD, **updates})


@pytest.mark.asyncio
async def test_run_scenario_returns_deterministic_metrics() -> None:
    service, _, _, _ = build_scenario_service()

    scenario = await run_scenario(scenario_request(), service, DESIGNER)

    assert scenario.id == "SCN-0001"
    assert scenario.name == "candidate-01"
    assert scenario.status == ScenarioStatus.SIMULATED
    assert scenario.config.num_robots == 3
    assert scenario.metrics.completed_tasks == 10
    assert scenario.metrics.unfinished_tasks == 0
    assert scenario.metrics.completion_rate == 1.0
    assert scenario.metrics.throughput_per_hour == 10.0
    assert scenario.metrics.average_cycle_time == 74.0
    assert scenario.metrics.average_waiting_time == 24.0
    assert scenario.duration_ms >= 0.0
    assert scenario.created_by == DESIGNER.id
    assert scenario.created_at is not None
    assert scenario.version == 1


@pytest.mark.asyncio
async def test_baseline_uses_repository_scenario() -> None:
    service, _, _, _ = build_scenario_service()

    baseline = await get_baseline(service)

    assert baseline.id == "baseline"
    assert baseline.name == "baseline"
    assert baseline.status == ScenarioStatus.SIMULATED
    assert baseline.config.num_robots == 3
    assert baseline.config.num_tasks == 500
    assert baseline.config.task_arrival_interval == 5.0
    assert baseline.config.travel_time == 30.0
    assert baseline.metrics.completed_tasks == 213
    assert baseline.metrics.unfinished_tasks == 287


@pytest.mark.asyncio
async def test_list_and_detail_return_in_memory_scenario() -> None:
    service, _, _, _ = build_scenario_service()
    created = await run_scenario(scenario_request(), service, DESIGNER)

    detail = await get_scenario(created.id, service)
    scenarios = await list_scenarios(service)

    assert detail.id == created.id
    assert [scenario.id for scenario in scenarios] == [created.id]


@pytest.mark.asyncio
async def test_apply_requires_approved_status() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await run_scenario(scenario_request(), service, DESIGNER)

    with pytest.raises(HTTPException) as error:
        await apply_scenario(scenario.id, service, MONITOR)

    assert error.value.status_code == 409
    assert "must be APPROVED" in str(error.value.detail)


@pytest.mark.asyncio
async def test_rejected_scenario_cannot_be_approved_or_applied() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await run_scenario(scenario_request(), service, DESIGNER)

    rejected = await reject_scenario(scenario.id, service, MONITOR)

    assert rejected.status == ScenarioStatus.REJECTED
    assert rejected.reviewed_at is not None
    for action in (approve_scenario, apply_scenario):
        with pytest.raises(HTTPException) as error:
            await action(scenario.id, service, MONITOR)
        assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_approve_then_apply_resets_realtime_factory() -> None:
    service, mock_factory, state, manager = build_scenario_service()
    broadcast = AsyncMock()
    manager.broadcast = broadcast
    scenario = await run_scenario(
        scenario_request(num_robots=4, task_arrival_interval=6.0, travel_time=45.0),
        service,
        DESIGNER,
    )

    approved = await approve_scenario(scenario.id, service, MONITOR)
    applied = await apply_scenario(scenario.id, service, MONITOR)

    assert approved.status == ScenarioStatus.APPROVED
    assert approved.reviewed_at is not None
    assert approved.reviewed_by == MONITOR.id
    assert approved.version == 2
    assert applied.status == ScenarioStatus.APPLIED
    assert applied.applied_at is not None
    assert applied.applied_by == MONITOR.id
    assert applied.version == 3
    assert mock_factory.config.robot_count == 4
    assert mock_factory.config.task_interval_seconds == 6.0
    assert len(state.list_robots()) == 4
    assert any(
        call.args[0] == {"type": "factory.reset", "data": None}
        for call in broadcast.await_args_list
    )


@pytest.mark.asyncio
async def test_service_rejects_creator_review_even_if_route_guard_is_bypassed() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await service.run(scenario_request(), DESIGNER)

    with pytest.raises(InvalidScenarioTransitionError, match="creator cannot"):
        await service.approve(scenario.id, DESIGNER)


@pytest.mark.asyncio
async def test_failed_apply_restores_factory_config_and_keeps_scenario_approved() -> None:
    service, mock_factory, _, _ = build_scenario_service()
    original_config = mock_factory.config.model_copy(deep=True)
    scenario = await service.run(
        scenario_request(num_robots=4, task_arrival_interval=6.0),
        DESIGNER,
    )
    approved = await service.approve(scenario.id, MONITOR)
    reset = AsyncMock(side_effect=[RuntimeError("reset failed"), None])
    mock_factory.reset = reset

    with pytest.raises(RuntimeError, match="reset failed"):
        await service.apply(approved.id, MONITOR)

    stored = await service.get(approved.id)
    assert stored.status == ScenarioStatus.APPROVED
    assert mock_factory.config == original_config
    assert reset.await_count == 2


@pytest.mark.asyncio
async def test_unknown_scenario_returns_404() -> None:
    service, _, _, _ = build_scenario_service()

    for action in (get_scenario, approve_scenario):
        with pytest.raises(HTTPException) as error:
            if action is approve_scenario:
                await action("SCN-9999", service, MONITOR)
            else:
                await action("SCN-9999", service)
        assert error.value.status_code == 404


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("num_robots", 0),
        ("num_tasks", 0),
        ("task_arrival_interval", 0),
        ("travel_time", 0),
        ("loading_time", 0),
        ("simulation_time", 0),
    ],
)
def test_invalid_scenario_is_rejected(field: str, value: str | int) -> None:
    with pytest.raises(ValidationError):
        scenario_request(**{field: value})


def test_openapi_exposes_scenario_workflow() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/scenarios/run" in paths
    assert "/api/v1/scenarios/baseline" in paths
    assert "/api/v1/scenarios/{scenario_id}/approve" in paths
    assert "/api/v1/scenarios/{scenario_id}/reject" in paths
    assert "/api/v1/scenarios/{scenario_id}/apply" in paths
