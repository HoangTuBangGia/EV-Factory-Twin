import asyncio
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
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager

DESIGNER = make_test_user(AppRole.DESIGNER)
MONITOR = make_test_user(AppRole.MONITOR)


async def setup(
    *, sweep_seconds: float = 1.0
) -> tuple[CommandService, ScenarioService, str, InMemoryRuntimeHistoryRepository]:
    manager = WebSocketManager()
    config = MockFactoryConfig()
    state = FactoryState(config)
    factory = MockFactory(state, config, manager, enabled=False)
    runtime_repository = InMemoryRuntimeHistoryRepository()
    runtime_health = RuntimeHealthService(
        state,
        runtime_repository,
        manager,
        stale_telemetry_seconds=5,
        bridge_disconnect_seconds=5,
        low_battery_percent=20,
        sweep_seconds=1,
    )
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
        CommandService(
            InMemoryCommandRepository(),
            scenarios,
            manager,
            InMemoryAuditRepository(),
            runtime_health,
            sweep_seconds=sweep_seconds,
        ),
        scenarios,
        scenario.id,
        runtime_repository,
    )


@pytest.mark.asyncio
async def test_positive_result_is_required_before_scenario_is_applied() -> None:
    commands, scenarios, scenario_id, _ = await setup()
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
    commands, scenarios, scenario_id, _ = await setup()
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
async def test_edge_payload_preserves_layout_and_route_identity() -> None:
    commands, scenarios, scenario_id, _ = await setup()
    scenario = await scenarios.get(scenario_id)
    command = await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)

    leased = await commands.lease("edge-main")

    assert leased is not None
    assert leased.payload.layout_id == scenario.config.layout_id
    assert leased.payload.layout_version == scenario.config.layout_version
    assert leased.payload.route_id == scenario.config.route_id
    assert command.payload == leased.payload


@pytest.mark.asyncio
async def test_duplicate_ack_and_result_are_idempotent() -> None:
    commands, scenarios, scenario_id, _ = await setup()
    command = await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
    await commands.lease("edge-main")
    acknowledgement = CommandAcknowledgementRequest(
        operation_id=command.operation_id, attempt_number=1, bridge_id="edge-main"
    )
    result = CommandResultRequest(
        operation_id=command.operation_id,
        attempt_number=1,
        bridge_id="edge-main",
        status=CommandStatus.COMPLETED,
        detail="layout applied",
    )

    first_ack = await commands.acknowledge(acknowledgement)
    duplicate_ack = await commands.acknowledge(acknowledgement)
    first_result = await commands.result(result)
    duplicate_result = await commands.result(result)

    assert duplicate_ack == first_ack
    assert duplicate_result == first_result
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPLIED


@pytest.mark.asyncio
async def test_late_result_from_old_attempt_cannot_complete_retry() -> None:
    commands, scenarios, scenario_id, _ = await setup()
    command = await commands.apply(
        scenario_id, ApplyScenarioRequest(timeout_seconds=0.01, max_retries=1), MONITOR
    )
    await commands.lease("edge-main")
    await commands.acknowledge(
        CommandAcknowledgementRequest(
            operation_id=command.operation_id, attempt_number=1, bridge_id="edge-main"
        )
    )
    await asyncio.sleep(0.02)
    await commands.retry(command.operation_id)

    with pytest.raises(CommandConflictError, match="attempt timed out"):
        await commands.result(
            CommandResultRequest(
                operation_id=command.operation_id,
                attempt_number=1,
                bridge_id="edge-main",
                status=CommandStatus.COMPLETED,
                detail="late success",
            )
        )

    current = await commands.get(command.operation_id)
    assert current.status == CommandStatus.PENDING
    assert current.attempts[0].status == CommandStatus.TIMED_OUT
    assert current.attempts[1].status == CommandStatus.PENDING
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPROVED


@pytest.mark.asyncio
async def test_edge_failure_reason_is_retained_without_applying_scenario() -> None:
    commands, scenarios, scenario_id, _ = await setup()
    command = await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
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
            detail="unsupported layout version factory-default@1",
        )
    )

    assert failed.attempts[0].detail == "unsupported layout version factory-default@1"
    assert (await scenarios.get(scenario_id)).status == ScenarioStatus.APPROVED


@pytest.mark.asyncio
async def test_expired_attempt_can_retry_within_budget() -> None:
    repository = InMemoryCommandRepository()
    commands, _, scenario_id, _ = await setup()
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
    commands, _, scenario_id, _ = await setup()
    await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)
    with pytest.raises(CommandConflictError, match="active"):
        await commands.apply(scenario_id, ApplyScenarioRequest(), MONITOR)


@pytest.mark.asyncio
async def test_timeout_alert_clears_on_retry() -> None:
    commands, _, scenario_id, runtime_repository = await setup()
    command = await commands.apply(
        scenario_id,
        ApplyScenarioRequest(timeout_seconds=0.01, max_retries=1),
        MONITOR,
    )
    await commands.lease("edge-main")
    await asyncio.sleep(0.02)

    assert (await commands.get(command.operation_id)).status == CommandStatus.TIMED_OUT
    assert (await runtime_repository.list_alerts())[0].code == "COMMAND_TIMEOUT"

    await commands.retry(command.operation_id)
    assert (await runtime_repository.list_alerts())[0].status == "CLEARED"


@pytest.mark.asyncio
async def test_background_sweep_expires_leased_command_without_api_poll() -> None:
    commands, _, scenario_id, runtime_repository = await setup(sweep_seconds=0.005)
    command = await commands.apply(
        scenario_id,
        ApplyScenarioRequest(timeout_seconds=0.01),
        MONITOR,
    )
    await commands.lease("edge-main")

    await commands.start()
    try:
        for _ in range(20):
            if await runtime_repository.list_alerts():
                break
            await asyncio.sleep(0.005)
    finally:
        await commands.stop()

    alerts = await runtime_repository.list_alerts()
    assert alerts[0].code == "COMMAND_TIMEOUT"
    assert (await commands.get(command.operation_id)).status == CommandStatus.TIMED_OUT


@pytest.mark.asyncio
async def test_background_sweep_expires_unleased_pending_command() -> None:
    commands, _, scenario_id, runtime_repository = await setup(sweep_seconds=0.005)
    command = await commands.apply(
        scenario_id,
        ApplyScenarioRequest(timeout_seconds=0.01),
        MONITOR,
    )

    await commands.start()
    try:
        for _ in range(20):
            if await runtime_repository.list_alerts():
                break
            await asyncio.sleep(0.005)
    finally:
        await commands.stop()

    alerts = await runtime_repository.list_alerts()
    assert alerts[0].code == "COMMAND_TIMEOUT"
    assert (await commands.get(command.operation_id)).status == CommandStatus.TIMED_OUT
