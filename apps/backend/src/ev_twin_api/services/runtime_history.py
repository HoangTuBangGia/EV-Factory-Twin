from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import text

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.alert import AlertStatus, FactoryAlert
from ev_twin_api.schemas.edge_runtime import BridgeHealth, TaskUpdate
from ev_twin_api.schemas.history import TaskHistoryItem, TelemetryHistoryItem
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

    async def list_telemetry(
        self,
        *,
        start: datetime,
        end: datetime,
        robot_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TelemetryHistoryItem]: ...

    async def list_tasks(
        self,
        *,
        start: datetime,
        end: datetime,
        task_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TaskHistoryItem]: ...

    async def activate_alert(self, alert: FactoryAlert) -> bool: ...
    async def clear_alert(self, dedupe_key: str, cleared_at: datetime) -> FactoryAlert | None: ...
    async def acknowledge_alert(
        self, alert_id: UUID, acknowledged_by: UUID, acknowledged_at: datetime
    ) -> FactoryAlert | None: ...
    async def list_alerts(self) -> list[FactoryAlert]: ...


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

    async def list_telemetry(
        self,
        *,
        start: datetime,
        end: datetime,
        robot_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TelemetryHistoryItem]:
        matches = sorted(
            (
                TelemetryHistoryItem(
                    telemetry=telemetry,
                    ingested_at=ingested_at,
                    ordering_status=ordering_status,
                )
                for telemetry, ingested_at, ordering_status in self.telemetry
                if start <= telemetry.timestamp <= end
                and (robot_id is None or telemetry.robot_id == robot_id)
            ),
            key=lambda item: (item.telemetry.timestamp, item.telemetry.robot_id),
        )
        return [item.model_copy(deep=True) for item in matches[offset : offset + limit]]

    async def list_tasks(
        self,
        *,
        start: datetime,
        end: datetime,
        task_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TaskHistoryItem]:
        matches = sorted(
            (
                TaskHistoryItem(update=update, ingested_at=ingested_at)
                for update, ingested_at in self.tasks
                if start <= ingested_at <= end
                and (task_id is None or update.task_id == task_id)
            ),
            key=lambda item: (item.ingested_at, item.update.task_id),
        )
        return [item.model_copy(deep=True) for item in matches[offset : offset + limit]]

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

    async def acknowledge_alert(
        self, alert_id: UUID, acknowledged_by: UUID, acknowledged_at: datetime
    ) -> FactoryAlert | None:
        alert = next((item for item in self.alerts if item.id == alert_id), None)
        if alert is None:
            return None
        if alert.acknowledged_at is None:
            alert.acknowledged_at = acknowledged_at
            alert.acknowledged_by = acknowledged_by
        return alert.model_copy(deep=True)

    async def list_alerts(self) -> list[FactoryAlert]:
        return [item.model_copy(deep=True) for item in reversed(self.alerts)]


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
                        task_id, payload_id, pickup_station_id, dropoff_station_id,
                        status, assigned_robot_id, attempt, max_retries, message,
                        source_timestamp, ingested_at
                    ) values (
                        :task_id, :payload_id, :pickup_station_id, :dropoff_station_id,
                        :status, :assigned_robot_id, :attempt, :max_retries, :message,
                        :source_timestamp, :ingested_at
                    ) on conflict (task_id, source_timestamp) do nothing
                """),
                {
                    "task_id": update.task_id,
                    "payload_id": update.payload_id,
                    "pickup_station_id": update.pickup_station_id,
                    "dropoff_station_id": update.dropoff_station_id,
                    "status": update.status.value,
                    "assigned_robot_id": update.assigned_robot_id,
                    "attempt": update.attempt,
                    "max_retries": update.max_retries,
                    "message": update.message,
                    "source_timestamp": update.updated_at,
                    "ingested_at": ingested_at,
                },
            )

    async def list_telemetry(
        self,
        *,
        start: datetime,
        end: datetime,
        robot_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TelemetryHistoryItem]:
        async with self._database.session() as session:
            result = await session.execute(
                text("""
                    select robot_id, source_timestamp, ingested_at, pose, velocity,
                        battery, status, task_id, payload_id, ordering_status
                    from public.robot_telemetry_history
                    where source_timestamp between :start and :end
                      and (cast(:robot_id as text) is null or robot_id = :robot_id)
                    order by source_timestamp, robot_id
                    limit :limit offset :offset
                """),
                {
                    "start": start,
                    "end": end,
                    "robot_id": robot_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            return [
                TelemetryHistoryItem(
                    telemetry=RobotTelemetry(
                        timestamp=row["source_timestamp"],
                        robot_id=row["robot_id"],
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

    async def list_tasks(
        self,
        *,
        start: datetime,
        end: datetime,
        task_id: str | None,
        limit: int,
        offset: int,
    ) -> list[TaskHistoryItem]:
        async with self._database.session() as session:
            result = await session.execute(
                text("""
                    select task_id, payload_id, pickup_station_id, dropoff_station_id,
                        status, assigned_robot_id, attempt, max_retries, message,
                        source_timestamp, ingested_at
                    from public.task_state_history
                    where ingested_at between :start and :end
                      and (cast(:task_id as text) is null or task_id = :task_id)
                    order by ingested_at, id
                    limit :limit offset :offset
                """),
                {
                    "start": start,
                    "end": end,
                    "task_id": task_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            return [
                TaskHistoryItem(
                    update=TaskUpdate(
                        task_id=row["task_id"],
                        payload_id=row["payload_id"],
                        pickup_station_id=row["pickup_station_id"],
                        dropoff_station_id=row["dropoff_station_id"],
                        assigned_robot_id=row["assigned_robot_id"],
                        status=row["status"],
                        attempt=row["attempt"],
                        max_retries=row["max_retries"],
                        message=row["message"],
                        updated_at=row["source_timestamp"],
                    ),
                    ingested_at=row["ingested_at"],
                )
                for row in result.mappings()
            ]

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
                        triggered_at timestamp, last_seen_at, cleared_at,
                        acknowledged_at, acknowledged_by
                """),
                {"dedupe_key": dedupe_key, "cleared_at": cleared_at},
            )
            row = result.mappings().one_or_none()
            return FactoryAlert.model_validate(row) if row is not None else None

    async def acknowledge_alert(
        self, alert_id: UUID, acknowledged_by: UUID, acknowledged_at: datetime
    ) -> FactoryAlert | None:
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    update public.alerts
                    set acknowledged_at=coalesce(acknowledged_at, :acknowledged_at),
                        acknowledged_by=coalesce(acknowledged_by, :acknowledged_by)
                    where id=:alert_id
                    returning id, dedupe_key, severity::text severity, code,
                        status::text status, message, robot_id, task_id, operation_id,
                        triggered_at timestamp, last_seen_at, cleared_at,
                        acknowledged_at, acknowledged_by
                """),
                {
                    "alert_id": alert_id,
                    "acknowledged_by": acknowledged_by,
                    "acknowledged_at": acknowledged_at,
                },
            )
            row = result.mappings().one_or_none()
            return FactoryAlert.model_validate(row) if row is not None else None

    async def list_alerts(self) -> list[FactoryAlert]:
        async with self._database.session() as session:
            result = await session.execute(
                text("""
                    select id, dedupe_key, severity::text severity, code,
                        status::text status, message, robot_id, task_id, operation_id,
                        triggered_at timestamp, last_seen_at, cleared_at,
                        acknowledged_at, acknowledged_by
                    from public.alerts order by triggered_at desc, id desc
                """)
            )
            return [FactoryAlert.model_validate(row) for row in result.mappings()]
