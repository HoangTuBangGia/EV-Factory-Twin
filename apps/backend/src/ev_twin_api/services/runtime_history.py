from datetime import datetime
from typing import Annotated, Protocol, cast

from fastapi import Depends, Request
from sqlalchemy import text

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.alert import AlertStatus, FactoryAlert
from ev_twin_api.schemas.edge_runtime import BridgeHealth, TaskUpdate
from ev_twin_api.schemas.history import TelemetryHistoryEntry
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus


class RuntimeHistoryRepository(Protocol):
    async def record_telemetry(
        self,
        telemetry: RobotTelemetry,
        ingested_at: datetime,
        ordering_status: TelemetryIngressStatus,
    ) -> None: ...

    async def record_bridge_health(self, health: BridgeHealth, ingested_at: datetime) -> None: ...

    async def record_task(self, update: TaskUpdate, ingested_at: datetime) -> None: ...

    async def activate_alert(self, alert: FactoryAlert) -> bool: ...
    async def clear_alert(self, dedupe_key: str, cleared_at: datetime) -> FactoryAlert | None: ...
    async def list_alerts(self) -> list[FactoryAlert]: ...
    async def list_telemetry(
        self,
        *,
        robot_id: str,
        start: datetime,
        end: datetime,
        before: datetime | None,
        limit: int,
    ) -> list[TelemetryHistoryEntry]: ...


class InMemoryRuntimeHistoryRepository:
    def __init__(self) -> None:
        self.telemetry: list[tuple[RobotTelemetry, datetime, TelemetryIngressStatus]] = []
        self.bridge_health: list[tuple[BridgeHealth, datetime]] = []
        self.tasks: list[tuple[TaskUpdate, datetime]] = []
        self.alerts: list[FactoryAlert] = []

    async def record_telemetry(
        self,
        telemetry: RobotTelemetry,
        ingested_at: datetime,
        ordering_status: TelemetryIngressStatus,
    ) -> None:
        if not any(
            item.robot_id == telemetry.robot_id and item.timestamp == telemetry.timestamp
            for item, _, _ in self.telemetry
        ):
            self.telemetry.append((telemetry.model_copy(deep=True), ingested_at, ordering_status))

    async def record_bridge_health(self, health: BridgeHealth, ingested_at: datetime) -> None:
        if not any(
            item.bridge_id == health.bridge_id and item.timestamp == health.timestamp
            for item, _ in self.bridge_health
        ):
            self.bridge_health.append((health.model_copy(deep=True), ingested_at))

    async def record_task(self, update: TaskUpdate, ingested_at: datetime) -> None:
        if not any(
            item.task_id == update.task_id and item.updated_at == update.updated_at
            for item, _ in self.tasks
        ):
            self.tasks.append((update.model_copy(deep=True), ingested_at))

    async def activate_alert(self, alert: FactoryAlert) -> bool:
        active = next(
            (
                item
                for item in self.alerts
                if item.dedupe_key == alert.dedupe_key and item.status == AlertStatus.ACTIVE
            ),
            None,
        )
        if active is not None:
            active.last_seen_at = alert.last_seen_at
            active.message = alert.message
            return False
        self.alerts.append(alert.model_copy(deep=True))
        return True

    async def clear_alert(self, dedupe_key: str, cleared_at: datetime) -> FactoryAlert | None:
        active = next(
            (
                item
                for item in self.alerts
                if item.dedupe_key == dedupe_key and item.status == AlertStatus.ACTIVE
            ),
            None,
        )
        if active is None:
            return None
        active.status = AlertStatus.CLEARED
        active.cleared_at = cleared_at
        active.last_seen_at = cleared_at
        return active.model_copy(deep=True)

    async def list_alerts(self) -> list[FactoryAlert]:
        return [item.model_copy(deep=True) for item in reversed(self.alerts)]

    async def list_telemetry(
        self,
        *,
        robot_id: str,
        start: datetime,
        end: datetime,
        before: datetime | None,
        limit: int,
    ) -> list[TelemetryHistoryEntry]:
        entries = (
            TelemetryHistoryEntry(
                telemetry=telemetry,
                ingested_at=ingested_at,
                ordering_status=ordering_status,
            )
            for telemetry, ingested_at, ordering_status in self.telemetry
            if telemetry.robot_id == robot_id
            and start <= telemetry.timestamp <= end
            and (before is None or telemetry.timestamp < before)
        )
        return sorted(entries, key=lambda entry: entry.telemetry.timestamp, reverse=True)[:limit]


class SqlAlchemyRuntimeHistoryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record_telemetry(
        self,
        telemetry: RobotTelemetry,
        ingested_at: datetime,
        ordering_status: TelemetryIngressStatus,
    ) -> None:
        async with self._database.session() as session, session.begin():
            await session.execute(
                text("""
                    insert into public.robot_telemetry_history (
                        robot_id, source_timestamp, ingested_at, pose, velocity, battery,
                        status, task_id, payload_id, ordering_status
                    ) values (
                        :robot_id, :source_timestamp, :ingested_at, cast(:pose as jsonb),
                        cast(:velocity as jsonb), :battery, :status, :task_id, :payload_id,
                        :ordering_status
                    ) on conflict (robot_id, source_timestamp) do nothing
                """),
                {
                    "robot_id": telemetry.robot_id,
                    "source_timestamp": telemetry.timestamp,
                    "ingested_at": ingested_at,
                    "pose": telemetry.pose.model_dump_json(),
                    "velocity": telemetry.velocity.model_dump_json(),
                    "battery": telemetry.battery,
                    "status": telemetry.status.value,
                    "task_id": telemetry.task_id,
                    "payload_id": telemetry.payload_id,
                    "ordering_status": (
                        "LATE"
                        if ordering_status == TelemetryIngressStatus.IGNORED_STALE
                        else "ACCEPTED"
                    ),
                },
            )

    async def record_bridge_health(self, health: BridgeHealth, ingested_at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            await session.execute(
                text("""
                    insert into public.bridge_health_history (
                        bridge_id, status, robot_ids, source_timestamp, ingested_at,
                        delivered_samples, failed_deliveries, last_error
                    ) values (
                        :bridge_id, :status, :robot_ids, :source_timestamp, :ingested_at,
                        :delivered_samples, :failed_deliveries, :last_error
                    ) on conflict (bridge_id, source_timestamp) do nothing
                """),
                {
                    **health.model_dump(mode="json", exclude={"timestamp"}),
                    "source_timestamp": health.timestamp,
                    "ingested_at": ingested_at,
                    "status": health.status.value,
                },
            )

    async def record_task(self, update: TaskUpdate, ingested_at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            await session.execute(
                text("""
                    insert into public.task_state_history (
                        task_id, status, assigned_robot_id, attempt, message,
                        source_timestamp, ingested_at
                    ) values (
                        :task_id, :status, :assigned_robot_id, :attempt, :message,
                        :source_timestamp, :ingested_at
                    ) on conflict (task_id, source_timestamp) do nothing
                """),
                {
                    "task_id": update.task_id,
                    "status": update.status.value,
                    "assigned_robot_id": update.assigned_robot_id,
                    "attempt": update.attempt,
                    "message": update.message,
                    "source_timestamp": update.updated_at,
                    "ingested_at": ingested_at,
                },
            )

    async def activate_alert(self, alert: FactoryAlert) -> bool:
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    insert into public.alerts (
                        id, dedupe_key, severity, code, status, message, robot_id,
                        task_id, operation_id, triggered_at, last_seen_at
                    ) values (
                        :id, :dedupe_key, cast(:severity as public.alert_severity), :code,
                        'ACTIVE', :message, :robot_id, :task_id, :operation_id,
                        :timestamp, :last_seen_at
                    ) on conflict (dedupe_key) where status = 'ACTIVE'
                    do update set last_seen_at=excluded.last_seen_at, message=excluded.message
                    returning id = :id as created
                """),
                alert.model_dump(),
            )
            return bool(result.scalar_one())

    async def clear_alert(self, dedupe_key: str, cleared_at: datetime) -> FactoryAlert | None:
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    update public.alerts set status='CLEARED', cleared_at=:cleared_at,
                        last_seen_at=:cleared_at
                    where dedupe_key=:dedupe_key and status='ACTIVE'
                    returning id, dedupe_key, severity::text severity, code,
                        status::text status, message, robot_id, task_id, operation_id,
                        triggered_at timestamp, last_seen_at, cleared_at
                """),
                {"dedupe_key": dedupe_key, "cleared_at": cleared_at},
            )
            row = result.mappings().one_or_none()
            return FactoryAlert.model_validate(row) if row is not None else None

    async def list_alerts(self) -> list[FactoryAlert]:
        async with self._database.session() as session:
            result = await session.execute(
                text("""
                    select id, dedupe_key, severity::text severity, code,
                        status::text status, message, robot_id, task_id, operation_id,
                        triggered_at timestamp, last_seen_at, cleared_at
                    from public.alerts order by triggered_at desc, id desc
                """)
            )
            return [FactoryAlert.model_validate(row) for row in result.mappings()]

    async def list_telemetry(
        self,
        *,
        robot_id: str,
        start: datetime,
        end: datetime,
        before: datetime | None,
        limit: int,
    ) -> list[TelemetryHistoryEntry]:
        clauses = [
            "robot_id = :robot_id",
            "source_timestamp >= :start",
            "source_timestamp <= :end",
        ]
        params: dict[str, object] = {
            "robot_id": robot_id,
            "start": start,
            "end": end,
            "limit": limit,
        }
        if before is not None:
            clauses.append("source_timestamp < :before")
            params["before"] = before
        async with self._database.session() as session:
            result = await session.execute(
                text(f"""
                    select robot_id, source_timestamp, ingested_at, pose, velocity,
                        battery, status, task_id, payload_id, ordering_status
                    from public.robot_telemetry_history
                    where {" and ".join(clauses)}
                    order by source_timestamp desc
                    limit :limit
                """),
                params,
            )
        return [
            TelemetryHistoryEntry(
                telemetry=RobotTelemetry(
                    robot_id=row["robot_id"],
                    timestamp=row["source_timestamp"],
                    pose=row["pose"],
                    velocity=row["velocity"],
                    battery=row["battery"],
                    status=row["status"],
                    task_id=row["task_id"],
                    payload_id=row["payload_id"],
                ),
                ingested_at=row["ingested_at"],
                ordering_status=(
                    TelemetryIngressStatus.IGNORED_STALE
                    if row["ordering_status"] == "LATE"
                    else TelemetryIngressStatus.ACCEPTED
                ),
            )
            for row in result.mappings()
        ]


def get_runtime_history_repository(request: Request) -> RuntimeHistoryRepository:
    return cast(RuntimeHistoryRepository, request.app.state.runtime_history_repository)


RuntimeHistoryRepositoryDep = Annotated[
    RuntimeHistoryRepository, Depends(get_runtime_history_repository)
]
