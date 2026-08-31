import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from conftest import make_test_user
from ev_twin_api.core.database import Database
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioMetrics,
    ScenarioRunRequest,
    ScenarioStatus,
)
from ev_twin_api.services.audit_service import InMemoryAuditRepository
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_repository import InMemoryLayoutRepository
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_repository import (
    SCENARIO_APPLY_SQL,
    SCENARIO_REVIEW_SQL,
    SCENARIO_SUBMIT_SQL,
    InMemoryScenarioRepository,
    ScenarioRepositoryConflictError,
    ScenarioRepositoryNotFoundError,
    SqlAlchemyScenarioRepository,
)
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.websocket_manager import WebSocketManager

CONFIG = ScenarioConfig(
    num_robots=3,
    num_tasks=10,
    task_arrival_interval=10,
    travel_time=30,
    loading_time=10,
    simulation_time=3600,
)
METRICS = ScenarioMetrics(
    completed_tasks=10,
    unfinished_tasks=0,
    completion_rate=1,
    throughput_per_hour=10,
    average_cycle_time=74,
    average_waiting_time=24,
)
DESIGNER = make_test_user(AppRole.DESIGNER)
MONITOR = make_test_user(AppRole.MONITOR)
NOW = datetime(2026, 8, 14, 3, 0, tzinfo=UTC)


async def create_scenario(repository: InMemoryScenarioRepository) -> Scenario:
    return await repository.create(
        name="candidate",
        config=CONFIG,
        metrics=METRICS,
        duration_ms=12.5,
        actor=DESIGNER,
        request_id=uuid4(),
        created_at=NOW,
    )


async def submit(repository: InMemoryScenarioRepository) -> Scenario:
    scenario = await create_scenario(repository)
    return await repository.transition(
        before=scenario,
        expected_status=ScenarioStatus.SIMULATED,
        new_status=ScenarioStatus.SUBMITTED,
        actor=DESIGNER,
        request_id=uuid4(),
        occurred_at=NOW,
    )


@pytest.mark.asyncio
async def test_create_persists_actor_and_audit_event() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)

    scenario = await create_scenario(repository)
    events = await audit.list(limit=10)

    assert scenario.created_by == DESIGNER.id
    assert scenario.created_at == NOW
    assert scenario.version == 1
    assert len(events) == 1
    assert events[0].action == AuditAction.SCENARIO_RUN
    assert events[0].actor_id == DESIGNER.id
    assert events[0].after_data is not None
    assert events[0].after_data["id"] == scenario.id


@pytest.mark.asyncio
async def test_scenario_survives_service_reconstruction_over_same_repository() -> None:
    repository = InMemoryScenarioRepository()
    factory_config = MockFactoryConfig()
    mock_factory = MockFactory(
        FactoryState(factory_config),
        factory_config,
        WebSocketManager(),
        enabled=False,
    )
    layouts = LayoutService(InMemoryLayoutRepository(include_default=True))
    first_service = ScenarioService(mock_factory, layout_service=layouts, repository=repository)
    created = await first_service.run(
        ScenarioRunRequest(name="restart-candidate", **CONFIG.model_dump()),
        DESIGNER,
    )

    reconstructed_service = ScenarioService(
        mock_factory, layout_service=layouts, repository=repository
    )
    detail = await reconstructed_service.get(created.id)
    scenarios = await reconstructed_service.list()

    assert detail == created
    assert [scenario.id for scenario in scenarios] == [created.id]


@pytest.mark.asyncio
async def test_creator_cannot_review_own_scenario() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)
    scenario = await submit(repository)

    with pytest.raises(ScenarioRepositoryConflictError, match="creator cannot"):
        await repository.transition(
            before=scenario,
            expected_status=ScenarioStatus.SUBMITTED,
            new_status=ScenarioStatus.APPROVED,
            actor=DESIGNER,
            request_id=uuid4(),
            occurred_at=NOW,
        )

    stored = await repository.get(scenario.id)
    events = await audit.list(limit=10)
    assert stored is not None
    assert stored.status == ScenarioStatus.SUBMITTED
    assert [event.action for event in events] == [
        AuditAction.SCENARIO_SUBMITTED,
        AuditAction.SCENARIO_RUN,
    ]


@pytest.mark.asyncio
async def test_only_one_concurrent_review_transition_wins() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)
    scenario = await submit(repository)

    async def transition(new_status: ScenarioStatus) -> Scenario:
        return await repository.transition(
            before=scenario,
            expected_status=ScenarioStatus.SUBMITTED,
            new_status=new_status,
            actor=MONITOR,
            request_id=uuid4(),
            occurred_at=NOW,
        )

    results = await asyncio.gather(
        transition(ScenarioStatus.APPROVED),
        transition(ScenarioStatus.REJECTED),
        return_exceptions=True,
    )

    assert sum(isinstance(result, Scenario) for result in results) == 1
    assert sum(isinstance(result, ScenarioRepositoryConflictError) for result in results) == 1
    stored = await repository.get(scenario.id)
    assert stored is not None
    assert stored.version == 3
    events = await audit.list(limit=10)
    assert len(events) == 3


@pytest.mark.asyncio
async def test_revision_request_persists_note_and_audit() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)
    scenario = await submit(repository)

    revised = await repository.transition(
        before=scenario,
        expected_status=ScenarioStatus.SUBMITTED,
        new_status=ScenarioStatus.REVISION_REQUESTED,
        actor=MONITOR,
        request_id=uuid4(),
        occurred_at=NOW,
        review_note="Move the charging zone away from the aisle.",
    )

    events = await audit.list(limit=10)
    assert revised.review_note == "Move the charging zone away from the aisle."
    assert events[0].action == AuditAction.SCENARIO_REVISION_REQUESTED
    assert events[0].after_data is not None
    assert events[0].after_data["review_note"] == revised.review_note


@pytest.mark.asyncio
async def test_apply_records_scenario_and_factory_reset_with_same_request_id() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)
    scenario = await submit(repository)
    approved = await repository.transition(
        before=scenario,
        expected_status=ScenarioStatus.SUBMITTED,
        new_status=ScenarioStatus.APPROVED,
        actor=MONITOR,
        request_id=uuid4(),
        occurred_at=NOW,
    )
    apply_request_id = uuid4()

    applied = await repository.transition(
        before=approved,
        expected_status=ScenarioStatus.APPROVED,
        new_status=ScenarioStatus.APPLIED,
        actor=MONITOR,
        request_id=apply_request_id,
        occurred_at=NOW,
    )

    events = await audit.list(limit=10)
    apply_events = [event for event in events if event.request_id == apply_request_id]
    assert applied.applied_by == MONITOR.id
    assert applied.version == 4
    assert {event.action for event in apply_events} == {
        AuditAction.SCENARIO_APPLIED,
        AuditAction.FACTORY_RESET,
    }


@pytest.mark.asyncio
async def test_failed_before_commit_hook_does_not_change_state_or_write_audit() -> None:
    audit = InMemoryAuditRepository()
    repository = InMemoryScenarioRepository(audit)
    scenario = await submit(repository)
    approved = await repository.transition(
        before=scenario,
        expected_status=ScenarioStatus.SUBMITTED,
        new_status=ScenarioStatus.APPROVED,
        actor=MONITOR,
        request_id=uuid4(),
        occurred_at=NOW,
    )

    async def fail(_: Scenario) -> None:
        raise RuntimeError("factory reset failed")

    with pytest.raises(RuntimeError, match="factory reset failed"):
        await repository.transition(
            before=approved,
            expected_status=ScenarioStatus.APPROVED,
            new_status=ScenarioStatus.APPLIED,
            actor=MONITOR,
            request_id=uuid4(),
            occurred_at=NOW,
            before_commit=fail,
        )

    stored = await repository.get(approved.id)
    events = await audit.list(limit=10)
    assert stored is not None
    assert stored.status == ScenarioStatus.APPROVED
    assert [event.action for event in events] == [
        AuditAction.SCENARIO_APPROVED,
        AuditAction.SCENARIO_SUBMITTED,
        AuditAction.SCENARIO_RUN,
    ]


class FakeMappings:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def one(self) -> dict[str, object]:
        assert len(self._rows) == 1
        return self._rows[0]

    def one_or_none(self) -> dict[str, object] | None:
        assert len(self._rows) <= 1
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, object]]:
        return self._rows


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._mappings = FakeMappings(rows or [])

    def mappings(self) -> FakeMappings:
        return self._mappings


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.transaction_entered += 1

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc, traceback
        self._session.transaction_commits.append(exc_type is None)


class FakeSession:
    def __init__(self, results: list[FakeResult]) -> None:
        self._results = results
        self.executions: list[tuple[str, dict[str, object]]] = []
        self.transaction_entered = 0
        self.transaction_commits: list[bool] = []

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(
        self,
        statement: object,
        params: dict[str, object] | None = None,
    ) -> FakeResult:
        self.executions.append((str(statement), params or {}))
        assert self._results, "unexpected SQL statement"
        return self._results.pop(0)


class FakeDatabase:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[FakeSession]:
        yield self._session


def scenario_row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "SCN-0042",
        "name": "candidate",
        "status": "SIMULATED",
        **CONFIG.model_dump(),
        **METRICS.model_dump(),
        "duration_ms": 12.5,
        "created_at": NOW,
        "created_by": DESIGNER.id,
        "reviewed_at": None,
        "reviewed_by": None,
        "review_note": None,
        "revision_of": None,
        "applied_at": None,
        "applied_by": None,
        "version": 1,
    }
    row.update(updates)
    return row


@pytest.mark.asyncio
async def test_sql_create_and_audit_share_one_transaction() -> None:
    session = FakeSession([FakeResult([scenario_row()]), FakeResult()])
    database = cast(Database, FakeDatabase(session))
    repository = SqlAlchemyScenarioRepository(database)

    scenario = await repository.create(
        name="candidate",
        config=CONFIG,
        metrics=METRICS,
        duration_ms=12.5,
        actor=DESIGNER,
        request_id=uuid4(),
        created_at=NOW,
    )

    assert scenario.id == "SCN-0042"
    assert session.transaction_entered == 1
    assert session.transaction_commits == [True]
    assert "INSERT INTO public.scenarios" in session.executions[0][0]
    assert "INSERT INTO public.audit_events" in session.executions[1][0]
    assert session.executions[1][1]["action"] == "SCENARIO_RUN"


def test_transition_sql_has_optimistic_lock_and_separation_guards() -> None:
    for statement in (SCENARIO_SUBMIT_SQL, SCENARIO_REVIEW_SQL, SCENARIO_APPLY_SQL):
        assert "version = :expected_version" in statement
        assert "version = version + 1" in statement
        assert "RETURNING" in statement
    assert "created_by = :actor_id" in SCENARIO_SUBMIT_SQL
    assert "created_by <> :actor_id" in SCENARIO_REVIEW_SQL
    assert "created_by <> :actor_id" in SCENARIO_APPLY_SQL
    assert "status = 'SUBMITTED'" in SCENARIO_REVIEW_SQL
    assert "status = 'APPROVED'" in SCENARIO_APPLY_SQL


@pytest.mark.asyncio
async def test_sql_transition_distinguishes_not_found_and_rolls_back() -> None:
    before = Scenario(
        id="SCN-0042",
        name="candidate",
        status=ScenarioStatus.SUBMITTED,
        config=CONFIG,
        metrics=METRICS,
        duration_ms=12.5,
        created_at=NOW,
        created_by=DESIGNER.id,
    )
    session = FakeSession([FakeResult(), FakeResult()])
    database = cast(Database, FakeDatabase(session))
    repository = SqlAlchemyScenarioRepository(database)

    with pytest.raises(ScenarioRepositoryNotFoundError):
        await repository.transition(
            before=before,
            expected_status=ScenarioStatus.SUBMITTED,
            new_status=ScenarioStatus.APPROVED,
            actor=MONITOR,
            request_id=UUID("00000000-0000-0000-0000-000000000099"),
            occurred_at=NOW,
        )

    assert session.transaction_commits == [False]
    assert "status = 'SUBMITTED'" in session.executions[0][0]
    assert "SELECT status::text AS status, version, created_by" in session.executions[1][0]
