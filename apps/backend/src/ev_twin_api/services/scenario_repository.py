import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, NoReturn, Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.schemas.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioMetrics,
    ScenarioStatus,
)
from ev_twin_api.services.audit_service import InMemoryAuditRepository, PendingAuditEvent
from ev_twin_api.services.audit_service import insert_audit_event as insert_sql_audit_event

SCENARIO_COLUMNS_SQL = """
id,
name,
status::text AS status,
num_robots,
num_tasks,
task_arrival_interval,
travel_time,
loading_time,
simulation_time,
layout_id,
layout_version,
route_id,
robot_speed_mps,
charger_count,
route_distance_m,
congestion_multiplier,
completed_tasks,
unfinished_tasks,
completion_rate,
throughput_per_hour,
average_cycle_time,
average_waiting_time,
fleet_utilization_percent,
starvation_events,
congestion_percent,
travel_distance,
average_delivery_delay,
duration_ms,
created_at,
created_by,
reviewed_at,
reviewed_by,
applied_at,
applied_by,
version
"""

SCENARIO_INSERT_SQL = f"""
INSERT INTO public.scenarios (
    name,
    status,
    num_robots,
    num_tasks,
    task_arrival_interval,
    travel_time,
    loading_time,
    simulation_time,
    layout_id,
    layout_version,
    route_id,
    robot_speed_mps,
    charger_count,
    route_distance_m,
    congestion_multiplier,
    completed_tasks,
    unfinished_tasks,
    completion_rate,
    throughput_per_hour,
    average_cycle_time,
    average_waiting_time,
    fleet_utilization_percent,
    starvation_events,
    congestion_percent,
    travel_distance,
    average_delivery_delay,
    duration_ms,
    created_by,
    created_at
)
VALUES (
    :name,
    'SIMULATED'::public.scenario_status,
    :num_robots,
    :num_tasks,
    :task_arrival_interval,
    :travel_time,
    :loading_time,
    :simulation_time,
    :layout_id,
    :layout_version,
    :route_id,
    :robot_speed_mps,
    :charger_count,
    :route_distance_m,
    :congestion_multiplier,
    :completed_tasks,
    :unfinished_tasks,
    :completion_rate,
    :throughput_per_hour,
    :average_cycle_time,
    :average_waiting_time,
    :fleet_utilization_percent,
    :starvation_events,
    :congestion_percent,
    :travel_distance,
    :average_delivery_delay,
    :duration_ms,
    :created_by,
    :created_at
)
RETURNING {SCENARIO_COLUMNS_SQL}
"""

SCENARIO_SELECT_SQL = f"SELECT {SCENARIO_COLUMNS_SQL} FROM public.scenarios"

SCENARIO_REVIEW_SQL = f"""
UPDATE public.scenarios
SET
    status = CAST(:new_status AS public.scenario_status),
    reviewed_by = :actor_id,
    reviewed_at = :occurred_at,
    version = version + 1
WHERE id = :scenario_id
  AND status = 'SUBMITTED'::public.scenario_status
  AND version = :expected_version
  AND created_by <> :actor_id
RETURNING {SCENARIO_COLUMNS_SQL}
"""

SCENARIO_SUBMIT_SQL = f"""
UPDATE public.scenarios
SET status = 'SUBMITTED'::public.scenario_status, version = version + 1
WHERE id = :scenario_id
  AND status = 'SIMULATED'::public.scenario_status
  AND version = :expected_version
  AND created_by = :actor_id
RETURNING {SCENARIO_COLUMNS_SQL}
"""

SCENARIO_APPLY_SQL = f"""
UPDATE public.scenarios
SET
    status = 'APPLIED'::public.scenario_status,
    applied_by = :actor_id,
    applied_at = :occurred_at,
    version = version + 1
WHERE id = :scenario_id
  AND status = 'APPROVED'::public.scenario_status
  AND version = :expected_version
  AND created_by <> :actor_id
RETURNING {SCENARIO_COLUMNS_SQL}
"""

SCENARIO_CONFLICT_SELECT_SQL = """
SELECT status::text AS status, version, created_by
FROM public.scenarios
WHERE id = :scenario_id
"""

TransitionHook = Callable[[Scenario], Awaitable[None]]


class ScenarioRepositoryNotFoundError(LookupError):
    pass


class ScenarioRepositoryConflictError(RuntimeError):
    pass


class ScenarioRepository(Protocol):
    async def create(
        self,
        *,
        name: str,
        config: ScenarioConfig,
        metrics: ScenarioMetrics,
        duration_ms: float,
        actor: CurrentUser,
        request_id: UUID,
        created_at: datetime,
    ) -> Scenario: ...

    async def list(self) -> list[Scenario]: ...

    async def get(self, scenario_id: str) -> Scenario | None: ...

    async def transition(
        self,
        *,
        before: Scenario,
        expected_status: ScenarioStatus,
        new_status: ScenarioStatus,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
        before_commit: TransitionHook | None = None,
    ) -> Scenario: ...


def scenario_to_audit_data(scenario: Scenario) -> dict[str, Any]:
    return scenario.model_dump(mode="json")


def _audit_action_for_status(status: ScenarioStatus) -> AuditAction:
    actions = {
        ScenarioStatus.SUBMITTED: AuditAction.SCENARIO_SUBMITTED,
        ScenarioStatus.APPROVED: AuditAction.SCENARIO_APPROVED,
        ScenarioStatus.REJECTED: AuditAction.SCENARIO_REJECTED,
        ScenarioStatus.APPLIED: AuditAction.SCENARIO_APPLIED,
    }
    try:
        return actions[status]
    except KeyError as error:
        raise ValueError(f"No audit action for scenario status {status}") from error


def _factory_reset_event(
    *,
    actor: CurrentUser,
    scenario: Scenario,
    request_id: UUID,
    occurred_at: datetime,
) -> PendingAuditEvent:
    return PendingAuditEvent(
        actor_id=actor.id,
        actor_role=actor.role,
        action=AuditAction.FACTORY_RESET,
        resource_type="factory",
        resource_id="mock-factory",
        before_data=None,
        after_data={
            "reason": "scenario_apply",
            "scenario_id": scenario.id,
            "scenario_version": scenario.version,
        },
        request_id=request_id,
        created_at=occurred_at,
    )


def _scenario_from_mapping(row: Any) -> Scenario:
    return Scenario(
        id=str(row["id"]),
        name=str(row["name"]),
        status=ScenarioStatus(str(row["status"])),
        config=ScenarioConfig(
            num_robots=int(row["num_robots"]),
            num_tasks=int(row["num_tasks"]),
            task_arrival_interval=float(row["task_arrival_interval"]),
            travel_time=float(row["travel_time"]),
            loading_time=float(row["loading_time"]),
            simulation_time=float(row["simulation_time"]),
            layout_id=str(row["layout_id"]),
            layout_version=int(row["layout_version"]),
            route_id=str(row["route_id"]),
            robot_speed_mps=float(row["robot_speed_mps"]),
            charger_count=int(row["charger_count"]),
            route_distance_m=float(row["route_distance_m"]),
            congestion_multiplier=float(row["congestion_multiplier"]),
        ),
        metrics=ScenarioMetrics(
            completed_tasks=int(row["completed_tasks"]),
            unfinished_tasks=int(row["unfinished_tasks"]),
            completion_rate=float(row["completion_rate"]),
            throughput_per_hour=float(row["throughput_per_hour"]),
            average_cycle_time=float(row["average_cycle_time"]),
            average_waiting_time=float(row["average_waiting_time"]),
            fleet_utilization_percent=float(row["fleet_utilization_percent"]),
            starvation_events=int(row["starvation_events"]),
            congestion_percent=float(row["congestion_percent"]),
            travel_distance=float(row["travel_distance"]),
            average_delivery_delay=float(row["average_delivery_delay"]),
        ),
        duration_ms=float(row["duration_ms"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
        reviewed_at=row["reviewed_at"],
        reviewed_by=row["reviewed_by"],
        applied_at=row["applied_at"],
        applied_by=row["applied_by"],
        version=int(row["version"]),
    )


class InMemoryScenarioRepository:
    """Fallback used only when the application has no DATABASE_URL."""

    def __init__(self, audit_repository: InMemoryAuditRepository | None = None) -> None:
        self.audit_repository = audit_repository or InMemoryAuditRepository()
        self._scenarios: dict[str, Scenario] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        name: str,
        config: ScenarioConfig,
        metrics: ScenarioMetrics,
        duration_ms: float,
        actor: CurrentUser,
        request_id: UUID,
        created_at: datetime,
    ) -> Scenario:
        async with self._lock:
            scenario_id = f"SCN-{self._next_id:04d}"
            scenario = Scenario(
                id=scenario_id,
                name=name,
                status=ScenarioStatus.SIMULATED,
                config=config,
                metrics=metrics,
                duration_ms=duration_ms,
                created_at=created_at,
                created_by=actor.id,
                version=1,
            )
            await self.audit_repository.record(
                PendingAuditEvent(
                    actor_id=actor.id,
                    actor_role=actor.role,
                    action=AuditAction.SCENARIO_RUN,
                    resource_type="scenario",
                    resource_id=scenario.id,
                    before_data=None,
                    after_data=scenario_to_audit_data(scenario),
                    request_id=request_id,
                    created_at=created_at,
                )
            )
            self._scenarios[scenario.id] = scenario
            self._next_id += 1
            return scenario.model_copy(deep=True)

    async def list(self) -> list[Scenario]:
        async with self._lock:
            scenarios = sorted(
                self._scenarios.values(),
                key=lambda scenario: scenario.created_at,
            )
            return [scenario.model_copy(deep=True) for scenario in scenarios]

    async def get(self, scenario_id: str) -> Scenario | None:
        async with self._lock:
            scenario = self._scenarios.get(scenario_id)
            return scenario.model_copy(deep=True) if scenario is not None else None

    async def transition(
        self,
        *,
        before: Scenario,
        expected_status: ScenarioStatus,
        new_status: ScenarioStatus,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
        before_commit: TransitionHook | None = None,
    ) -> Scenario:
        async with self._lock:
            current = self._scenarios.get(before.id)
            if current is None:
                raise ScenarioRepositoryNotFoundError(f"Scenario '{before.id}' not found")
            if current.status != expected_status or current.version != before.version:
                raise ScenarioRepositoryConflictError(
                    f"Scenario '{before.id}' changed concurrently or cannot transition from "
                    f"{current.status} to {new_status}"
                )
            if new_status == ScenarioStatus.SUBMITTED and current.created_by != actor.id:
                raise ScenarioRepositoryConflictError(
                    f"Scenario '{before.id}' can only be submitted by its creator"
                )
            if new_status != ScenarioStatus.SUBMITTED and current.created_by == actor.id:
                raise ScenarioRepositoryConflictError(
                    f"Scenario '{before.id}' creator cannot review or apply their own scenario"
                )

            if new_status == ScenarioStatus.SUBMITTED:
                after = current.with_status(new_status)
            elif new_status in {ScenarioStatus.APPROVED, ScenarioStatus.REJECTED}:
                after = current.with_status(
                    new_status,
                    reviewed_at=occurred_at,
                    reviewed_by=actor.id,
                )
            elif new_status == ScenarioStatus.APPLIED:
                after = current.with_status(
                    new_status,
                    applied_at=occurred_at,
                    applied_by=actor.id,
                )
            else:
                raise ValueError(f"Unsupported scenario transition to {new_status}")

            if before_commit is not None:
                await before_commit(after.model_copy(deep=True))
            await self.audit_repository.record(
                PendingAuditEvent(
                    actor_id=actor.id,
                    actor_role=actor.role,
                    action=_audit_action_for_status(new_status),
                    resource_type="scenario",
                    resource_id=after.id,
                    before_data=scenario_to_audit_data(current),
                    after_data=scenario_to_audit_data(after),
                    request_id=request_id,
                    created_at=occurred_at,
                )
            )
            if new_status == ScenarioStatus.APPLIED:
                await self.audit_repository.record(
                    _factory_reset_event(
                        actor=actor,
                        scenario=after,
                        request_id=request_id,
                        occurred_at=occurred_at,
                    )
                )
            self._scenarios[after.id] = after
            return after.model_copy(deep=True)


class SqlAlchemyScenarioRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(
        self,
        *,
        name: str,
        config: ScenarioConfig,
        metrics: ScenarioMetrics,
        duration_ms: float,
        actor: CurrentUser,
        request_id: UUID,
        created_at: datetime,
    ) -> Scenario:
        params: dict[str, object] = {
            "name": name,
            **config.model_dump(),
            **metrics.model_dump(),
            "duration_ms": duration_ms,
            "created_by": actor.id,
            "created_at": created_at,
        }
        async with self._database.session() as session, session.begin():
            result = await session.execute(text(SCENARIO_INSERT_SQL), params)
            scenario = _scenario_from_mapping(result.mappings().one())
            await insert_sql_audit_event(
                session,
                PendingAuditEvent(
                    actor_id=actor.id,
                    actor_role=actor.role,
                    action=AuditAction.SCENARIO_RUN,
                    resource_type="scenario",
                    resource_id=scenario.id,
                    before_data=None,
                    after_data=scenario_to_audit_data(scenario),
                    request_id=request_id,
                    created_at=created_at,
                ),
            )
        return scenario

    async def list(self) -> list[Scenario]:
        async with self._database.session() as session:
            result = await session.execute(
                text(f"{SCENARIO_SELECT_SQL} ORDER BY created_at ASC, id ASC")
            )
        return [_scenario_from_mapping(row) for row in result.mappings().all()]

    async def get(self, scenario_id: str) -> Scenario | None:
        async with self._database.session() as session:
            result = await session.execute(
                text(f"{SCENARIO_SELECT_SQL} WHERE id = :scenario_id"),
                {"scenario_id": scenario_id},
            )
        row = result.mappings().one_or_none()
        return _scenario_from_mapping(row) if row is not None else None

    async def transition(
        self,
        *,
        before: Scenario,
        expected_status: ScenarioStatus,
        new_status: ScenarioStatus,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
        before_commit: TransitionHook | None = None,
    ) -> Scenario:
        if expected_status == ScenarioStatus.SIMULATED and new_status == ScenarioStatus.SUBMITTED:
            statement = SCENARIO_SUBMIT_SQL
        elif expected_status == ScenarioStatus.SUBMITTED and new_status in {
            ScenarioStatus.APPROVED,
            ScenarioStatus.REJECTED,
        }:
            statement = SCENARIO_REVIEW_SQL
        elif expected_status == ScenarioStatus.APPROVED and new_status == ScenarioStatus.APPLIED:
            statement = SCENARIO_APPLY_SQL
        else:
            raise ValueError(f"Unsupported scenario transition {expected_status} -> {new_status}")

        params: dict[str, object] = {
            "scenario_id": before.id,
            "expected_version": before.version,
            "new_status": new_status.value,
            "actor_id": actor.id,
            "occurred_at": occurred_at,
        }
        async with self._database.session() as session, session.begin():
            result = await session.execute(text(statement), params)
            row = result.mappings().one_or_none()
            if row is None:
                await self._raise_transition_failure(session, before, new_status)

            after = _scenario_from_mapping(row)
            if before_commit is not None:
                await before_commit(after)
            await insert_sql_audit_event(
                session,
                PendingAuditEvent(
                    actor_id=actor.id,
                    actor_role=actor.role,
                    action=_audit_action_for_status(new_status),
                    resource_type="scenario",
                    resource_id=after.id,
                    before_data=scenario_to_audit_data(before),
                    after_data=scenario_to_audit_data(after),
                    request_id=request_id,
                    created_at=occurred_at,
                ),
            )
            if new_status == ScenarioStatus.APPLIED:
                await insert_sql_audit_event(
                    session,
                    _factory_reset_event(
                        actor=actor,
                        scenario=after,
                        request_id=request_id,
                        occurred_at=occurred_at,
                    ),
                )
        return after

    async def _raise_transition_failure(
        self,
        session: AsyncSession,
        before: Scenario,
        new_status: ScenarioStatus,
    ) -> NoReturn:
        result = await session.execute(
            text(SCENARIO_CONFLICT_SELECT_SQL),
            {"scenario_id": before.id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ScenarioRepositoryNotFoundError(f"Scenario '{before.id}' not found")
        raise ScenarioRepositoryConflictError(
            f"Scenario '{before.id}' changed concurrently or cannot transition from "
            f"{row['status']} to {new_status}"
        )
