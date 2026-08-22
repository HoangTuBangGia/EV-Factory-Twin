from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from conftest import make_test_user
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.command import (
    ApplyScenarioRequest,
    Command,
    CommandAcknowledgementRequest,
    CommandAttempt,
    CommandResultRequest,
    CommandStatus,
)
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import ScenarioRunRequest, ScenarioStatus
from ev_twin_api.services.audit_service import InMemoryAuditRepository
from ev_twin_api.services.command_service import (
    CommandConflictError,
    CommandService,
    InMemoryCommandRepository,
)
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_repository import InMemoryLayoutRepository
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager

DESIGNER = make_test_user(AppRole.DESIGNER)
MONITOR = make_test_user(AppRole.MONITOR)


async def setup() -> tuple[CommandService, ScenarioService, str]:
    manager = WebSocketManager()
    config = MockFactoryConfig()
    factory = MockFactory(FactoryState(config), config, manager, enabled=False)
    scenarios = ScenarioService(
        factory,
        layout_service=LayoutService(InMemoryLayoutRepository(include_default=True)),
    )
    scenario = await scenarios.run(
        ScenarioRunRequest(
            name="apply-me",
            num_robots=3,
            num_tasks=10,
            task_arrival_interval=8,
            travel_time=1,
            loading_time=2,
            simulation_time=100,
        ),
        DESIGNER,
    )
    await scenarios.submit(scenario.id, DESIGNER)
    await scenarios.approve(scenario.id, MONITOR)
    return (
        CommandService(InMemoryCommandRepository(), scenarios, manager, InMemoryAuditRepository()),
        scenarios,
        scenario.id,
    )


@pytest.mark.asyncio
async def test_positive_result_is_required_before_scenario_is_applied() -> None:
    commands, scenarios, scenario_id = await setup()
    command = await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
    leased = await commands.lease("edge-main")
    assert leased is not None
    await commands.acknowledge(
        CommandAcknowledgementRequest(
            operation_id=command.operation_id, attempt_number=1, bridge_id="edge-main"
        )
    )
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPROVED

    completed = await commands.result(
        CommandResultRequest(
            operation_id=command.operation_id,
            attempt_number=1,
            bridge_id="edge-main",
            status=CommandStatus.COMPLETED,
        )
    )

    assert completed.status == CommandStatus.COMPLETED
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPLIED


@pytest.mark.asyncio
async def test_failed_result_keeps_scenario_approved_and_retry_reuses_operation() -> None:
    commands, scenarios, scenario_id = await setup()
    command = await commands.apply(scenario_id, ApplyScenarioRequest(max_retries=1), MONITOR)
    await commands.lease("edge-main")
    await commands.acknowledge(
        CommandAcknowledgementRequest(
            operation_id=command.operation_id, attempt_number=1, bridge_id="edge-main"
        )
    )
    failed = await commands.result(
        CommandResultRequest(
            operation_id=command.operation_id,
            attempt_number=1,
            bridge_id="edge-main",
            status=CommandStatus.FAILED,
            detail="topology requires relaunch",
        )
    )
    retried = await commands.retry(command.operation_id)

    assert failed.status == CommandStatus.FAILED
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPROVED
    assert retried.operation_id == command.operation_id
    assert retried.attempts[-1].attempt_number == 2


@pytest.mark.asyncio
async def test_expired_attempt_can_retry_within_budget() -> None:
    repository = InMemoryCommandRepository()
    commands, _, scenario_id = await setup()
    del commands
    now = datetime.now(UTC)
    command = Command(
        operation_id=uuid4(),
        scenario_id=scenario_id,
        status=CommandStatus.PENDING,
        payload=ScenarioRunRequest(
            name="x",
            num_robots=2,
            num_tasks=1,
            task_arrival_interval=1,
            travel_time=1,
            loading_time=1,
            simulation_time=10,
        ).to_config(),
        timeout_seconds=1,
        max_retries=1,
        attempts=[CommandAttempt(attempt_number=1, status=CommandStatus.PENDING)],
        requested_by=MONITOR.id,
        created_at=now,
        updated_at=now,
    )
    await repository.create(command)
    await repository.lease("edge", now)
    retried = await repository.retry(command.operation_id, now + timedelta(seconds=2))
    assert retried.attempts[0].status == CommandStatus.TIMED_OUT
    assert retried.attempts[1].status == CommandStatus.PENDING


@pytest.mark.asyncio
async def test_cannot_create_two_active_commands_for_one_scenario() -> None:
    commands, _, scenario_id = await setup()
    await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
    with pytest.raises(CommandConflictError, match="active"):
        await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
