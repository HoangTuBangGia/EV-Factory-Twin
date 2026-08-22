import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from conftest import make_test_user
from ev_twin_api.api.mock import reset_mock, update_mock_config
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import ScenarioRunRequest, ScenarioStatus
from ev_twin_api.services.audit_service import (
    AuditService,
    InMemoryAuditRepository,
)
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_repository import InMemoryLayoutRepository
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager

DESIGNER = make_test_user(AppRole.DESIGNER)
MONITOR = make_test_user(AppRole.MONITOR)


def build_mock_factory() -> MockFactory:
    config = MockFactoryConfig()
    return MockFactory(
        FactoryState(config),
        config,
        WebSocketManager(),
        enabled=False,
    )


@pytest.mark.asyncio
async def test_reset_does_not_mutate_factory_when_intent_audit_fails() -> None:
    mock_factory = build_mock_factory()
    mock_factory.reset = AsyncMock()
    audit_service = AsyncMock(spec=AuditService)
    audit_service.record.side_effect = RuntimeError("audit unavailable")

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await reset_mock(mock_factory, audit_service, MONITOR)

    mock_factory.reset.assert_not_awaited()


@pytest.mark.asyncio
async def test_config_does_not_mutate_factory_when_intent_audit_fails() -> None:
    mock_factory = build_mock_factory()
    original_config = mock_factory.config.model_copy(deep=True)
    mock_factory.apply_config = Mock(wraps=mock_factory.apply_config)
    audit_service = AsyncMock(spec=AuditService)
    audit_service.record.side_effect = RuntimeError("audit unavailable")

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await update_mock_config(
            MockFactoryConfig(robot_count=7),
            mock_factory,
            audit_service,
            MONITOR,
        )

    mock_factory.apply_config.assert_not_called()
    assert mock_factory.config == original_config


@pytest.mark.asyncio
async def test_manual_reset_waits_for_scenario_apply_control_lock() -> None:
    mock_factory = build_mock_factory()
    service = ScenarioService(
        mock_factory,
        layout_service=LayoutService(InMemoryLayoutRepository(include_default=True)),
    )
    scenario = await service.run(
        ScenarioRunRequest(
            name="serialized-controls",
            num_robots=4,
            num_tasks=10,
            task_arrival_interval=10,
            travel_time=30,
            loading_time=10,
            simulation_time=3600,
        ),
        DESIGNER,
    )
    await service.submit(scenario.id, DESIGNER)
    approved = await service.approve(scenario.id, MONITOR)

    first_reset_started = asyncio.Event()
    allow_first_reset = asyncio.Event()
    original_reset = mock_factory.reset
    reset_count = 0

    async def controlled_reset() -> None:
        nonlocal reset_count
        reset_count += 1
        if reset_count == 1:
            first_reset_started.set()
            await allow_first_reset.wait()
        await original_reset()

    mock_factory.reset = controlled_reset
    audit_repository = InMemoryAuditRepository()
    audit_service = AuditService(audit_repository)

    apply_task = asyncio.create_task(service.complete_apply(approved.id, MONITOR))
    await first_reset_started.wait()
    manual_reset_task = asyncio.create_task(reset_mock(mock_factory, audit_service, MONITOR))
    await asyncio.sleep(0)

    assert not manual_reset_task.done()
    assert await audit_repository.list(limit=10) == []

    allow_first_reset.set()
    applied, _ = await asyncio.gather(apply_task, manual_reset_task)

    assert applied.status == ScenarioStatus.APPLIED
    assert reset_count == 2
    events = await audit_repository.list(limit=10)
    assert [event.action.value for event in events] == [
        "FACTORY_RESET",
        "FACTORY_RESET_REQUESTED",
    ]
