from collections.abc import Callable
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
    request_scenario_revision,
    run_scenario,
    submit_scenario,
)
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.command import (
    ApplyScenarioRequest,
    CommandAcknowledgementRequest,
    CommandResultRequest,
    CommandStatus,
)
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.layout import CreateLayoutRequest
from ev_twin_api.schemas.scenario import (
    ScenarioRevisionRequest,
    ScenarioRunRequest,
    ScenarioStatus,
)
from ev_twin_api.services.audit_service import InMemoryAuditRepository
from ev_twin_api.services.command_service import CommandService, InMemoryCommandRepository
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_repository import InMemoryLayoutRepository
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_service import InvalidScenarioTransitionError, ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager
from fastapi import HTTPException
from pydantic import ValidationError
from twin_core.default_layout import default_layout_content
from twin_core.models.layout import LayoutVersion

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


def build_scenario_service(
    applied_layout_sink: Callable[[LayoutVersion], None] | None = None,
    *,
    apply_to_mock_runtime: bool = True,
) -> tuple[ScenarioService, MockFactory, FactoryState, WebSocketManager]:
    config = MockFactoryConfig()
    manager = WebSocketManager()
    state = FactoryState(config, seed_mock_robots=apply_to_mock_runtime)
    mock_factory = MockFactory(state, config, manager, enabled=apply_to_mock_runtime)
    return (
        ScenarioService(
            mock_factory,
            layout_service=LayoutService(InMemoryLayoutRepository(include_default=True)),
            applied_layout_sink=applied_layout_sink,
            apply_to_mock_runtime=apply_to_mock_runtime,
        ),
        mock_factory,
        state,
        manager,
    )


def scenario_request(**updates: object) -> ScenarioRunRequest:
    return ScenarioRunRequest.model_validate({**SCENARIO_PAYLOAD, **updates})


@pytest.mark.asyncio
async def test_run_scenario_returns_deterministic_metrics() -> None:
    service, _, _, _ = build_scenario_service()

    scenario = await run_scenario(scenario_request(), service, DESIGNER)
    repeated = await run_scenario(scenario_request(name="candidate-02"), service, DESIGNER)

    assert scenario.id == "SCN-0001"
    assert scenario.name == "candidate-01"
    assert scenario.status == ScenarioStatus.SIMULATED
    assert scenario.config.num_robots == 3
    assert scenario.config.layout_id == "LAYOUT-DEFAULT"
    assert scenario.metrics.completed_tasks + scenario.metrics.unfinished_tasks == 10
    assert scenario.metrics == repeated.metrics
    assert scenario.duration_ms >= 0.0
    assert scenario.created_by == DESIGNER.id
    assert scenario.created_at is not None
    assert scenario.version == 1


@pytest.mark.asyncio
async def test_baseline_uses_repository_scenario() -> None:
    service, factory, _, _ = build_scenario_service()
    service = ScenarioService(
        factory,
        layout_service=LayoutService(InMemoryLayoutRepository(include_default=True)),
    )

    baseline = await get_baseline(service)

    assert baseline.id == "baseline"
    assert baseline.name == "baseline"
    assert baseline.status == ScenarioStatus.SIMULATED
    assert baseline.config.num_robots == 3
    assert baseline.config.num_tasks == 500
    assert baseline.config.task_arrival_interval == 5.0
    assert baseline.config.layout_id == "LAYOUT-DEFAULT"
    assert baseline.config.layout_version == 3
    assert baseline.config.route_id == "BATTERY_DELIVERY"
    assert baseline.config.travel_time != 30.0
    assert baseline.metrics.completed_tasks + baseline.metrics.unfinished_tasks == 500
    assert baseline.metrics.travel_distance > 0.0
    assert baseline.metrics.fleet_utilization_percent > 0.0


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
    service, _, _, manager = build_scenario_service()
    commands = CommandService(
        InMemoryCommandRepository(), service, manager, InMemoryAuditRepository()
    )
    scenario = await run_scenario(scenario_request(), service, DESIGNER)

    with pytest.raises(HTTPException) as error:
        await apply_scenario(scenario.id, ApplyScenarioRequest(), commands, MONITOR)

    assert error.value.status_code == 409
    assert "must be APPROVED" in str(error.value.detail)


@pytest.mark.asyncio
async def test_rejected_scenario_cannot_be_approved_or_applied() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await run_scenario(scenario_request(), service, DESIGNER)
    await submit_scenario(scenario.id, service, DESIGNER)
    rejected = await reject_scenario(scenario.id, service, MONITOR)

    assert rejected.status == ScenarioStatus.REJECTED
    assert rejected.reviewed_at is not None
    with pytest.raises(HTTPException) as error:
        await approve_scenario(scenario.id, service, MONITOR)
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_monitor_requests_revision_and_creator_runs_linked_candidate() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await run_scenario(scenario_request(), service, DESIGNER)
    await submit_scenario(scenario.id, service, DESIGNER)

    requested = await request_scenario_revision(
        scenario.id,
        ScenarioRevisionRequest(note="Move the charging zone away from the aisle."),
        service,
        MONITOR,
    )
    revised = await run_scenario(
        scenario_request(name="candidate-02", revision_of=scenario.id),
        service,
        DESIGNER,
    )

    assert requested.status == ScenarioStatus.REVISION_REQUESTED
    assert requested.review_note == "Move the charging zone away from the aisle."
    assert revised.status == ScenarioStatus.SIMULATED
    assert revised.revision_of == scenario.id


@pytest.mark.asyncio
async def test_revision_must_reference_owned_revision_requested_scenario() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await run_scenario(scenario_request(), service, DESIGNER)

    with pytest.raises(HTTPException) as error:
        await run_scenario(
            scenario_request(name="invalid-revision", revision_of=scenario.id),
            service,
            DESIGNER,
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_apply_waits_for_positive_command_result() -> None:
    projected_layouts: list[LayoutVersion] = []
    service, mock_factory, state, manager = build_scenario_service(projected_layouts.append)
    broadcast = AsyncMock()
    manager.broadcast = broadcast
    scenario = await run_scenario(
        scenario_request(num_robots=4, task_arrival_interval=6.0, travel_time=45.0),
        service,
        DESIGNER,
    )
    submitted = await submit_scenario(scenario.id, service, DESIGNER)
    approved = await approve_scenario(scenario.id, service, MONITOR)
    commands = CommandService(
        InMemoryCommandRepository(), service, manager, InMemoryAuditRepository()
    )
    command = await apply_scenario(scenario.id, ApplyScenarioRequest(), commands, MONITOR)
    leased = await commands.lease("edge-test")
    assert leased is not None
    await commands.acknowledge(
        CommandAcknowledgementRequest(
            operation_id=command.operation_id, attempt_number=1, bridge_id="edge-test"
        )
    )
    assert (await service.get(scenario.id)).status == ScenarioStatus.APPROVED
    applied_command = await commands.result(
        CommandResultRequest(
            operation_id=command.operation_id,
            attempt_number=1,
            bridge_id="edge-test",
            status=CommandStatus.COMPLETED,
        )
    )
    applied = await service.get(scenario.id)

    assert submitted.status == ScenarioStatus.SUBMITTED
    assert approved.status == ScenarioStatus.APPROVED
    assert approved.reviewed_at is not None
    assert approved.reviewed_by == MONITOR.id
    assert approved.version == 3
    assert applied_command.status == CommandStatus.COMPLETED
    assert applied.status == ScenarioStatus.APPLIED
    assert applied.applied_at is not None
    assert applied.applied_by == MONITOR.id
    assert applied.version == 4
    assert mock_factory.config.robot_count == 4
    assert mock_factory.config.task_interval_seconds == 6.0
    assert len(state.list_robots()) == 4
    assert [(layout.layout_id, layout.version) for layout in projected_layouts] == [
        ("LAYOUT-DEFAULT", 3)
    ]
    restored_layout = await service.get_applied_layout()
    assert restored_layout is not None
    assert (restored_layout.layout_id, restored_layout.version) == ("LAYOUT-DEFAULT", 3)
    assert any(
        call.args[0] == {"type": "factory.reset", "data": None}
        for call in broadcast.await_args_list
    )


@pytest.mark.asyncio
async def test_ros_apply_completion_does_not_reset_edge_runtime_state() -> None:
    service, mock_factory, state, _ = build_scenario_service(apply_to_mock_runtime=False)
    state.synchronize_robot_registry(["EDGE-01", "EDGE-02"])
    scenario = await service.run(scenario_request(num_robots=4), DESIGNER)
    await service.submit(scenario.id, DESIGNER)
    approved = await service.approve(scenario.id, MONITOR)
    mock_factory.reset = AsyncMock()

    applied = await service.complete_apply(approved.id, MONITOR)

    assert applied.status == ScenarioStatus.APPLIED
    assert {robot.id for robot in state.list_robots()} == {"EDGE-01", "EDGE-02"}
    mock_factory.reset.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_projects_selected_layout_geometry_into_mock_runtime() -> None:
    layout_repository = InMemoryLayoutRepository()
    layout_service = LayoutService(layout_repository)
    content = default_layout_content().model_dump(mode="json")
    content["stations"][0].update({"x": 28, "y": 28})
    for route in content["routes"]:
        if route["start_station_id"] == "BATTERY_BUFFER":
            route["waypoints"][0] = {"x": 28, "y": 28}
        if route["end_station_id"] == "BATTERY_BUFFER":
            route["waypoints"][-1] = {"x": 28, "y": 28}
    created_layout = await layout_service.create(
        CreateLayoutRequest(name="Moved buffer", content=content),
        DESIGNER,
    )
    config = MockFactoryConfig()
    state = FactoryState(config)
    mock_factory = MockFactory(state, config, WebSocketManager(), enabled=False)
    service = ScenarioService(mock_factory, layout_service=layout_service)
    scenario = await service.run(
        scenario_request(
            layout_id=created_layout.layout_id,
            layout_version=created_layout.version,
        ),
        DESIGNER,
    )
    await service.submit(scenario.id, DESIGNER)
    approved = await service.approve(scenario.id, MONITOR)

    await service.complete_apply(approved.id, MONITOR)

    buffer = next(station for station in state.stations if station.id == "BATTERY_BUFFER")
    assert (buffer.x, buffer.y) == (28, 28)
    assert state.route_waypoints(("BATTERY_BUFFER", "MARRIAGE_STATION"))[0] == (28, 28)


@pytest.mark.asyncio
async def test_service_rejects_creator_review_even_if_route_guard_is_bypassed() -> None:
    service, _, _, _ = build_scenario_service()
    scenario = await service.run(scenario_request(), DESIGNER)
    await service.submit(scenario.id, DESIGNER)
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
    await service.submit(scenario.id, DESIGNER)
    approved = await service.approve(scenario.id, MONITOR)
    reset = AsyncMock(side_effect=[RuntimeError("reset failed"), None])
    mock_factory.reset = reset

    with pytest.raises(RuntimeError, match="reset failed"):
        await service.complete_apply(approved.id, MONITOR)

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
    assert "/api/v1/scenarios/{scenario_id}/submit" in paths
    assert "/api/v1/scenarios/{scenario_id}/approve" in paths
    assert "/api/v1/scenarios/{scenario_id}/reject" in paths
    assert "/api/v1/scenarios/{scenario_id}/request-revision" in paths
    assert "/api/v1/scenarios/{scenario_id}/apply" in paths
