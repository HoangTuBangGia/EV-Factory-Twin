import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import text

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.history import KpiHistoryItem
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.services.factory_state import FactoryState

logger = logging.getLogger("ev_twin_api")

KPI_SNAPSHOT_INTERVAL_SECONDS = 10.0

KPI_SNAPSHOT_INSERT_SQL = """
INSERT INTO public.kpi_snapshots (
    scenario_id,
    recorded_at,
    simulated_elapsed_seconds,
    completed_tasks,
    throughput_per_hour,
    average_cycle_time_seconds,
    active_tasks,
    queued_tasks,
    starvation_events,
    fleet_utilization_percent
)
VALUES (
    :scenario_id,
    :recorded_at,
    :simulated_elapsed_seconds,
    :completed_tasks,
    :throughput_per_hour,
    :average_cycle_time_seconds,
    :active_tasks,
    :queued_tasks,
    :starvation_events,
    :fleet_utilization_percent
)
"""


@dataclass(frozen=True, slots=True)
class KpiSnapshot:
    """One factory-wide KPI sample; it intentionally contains no robot telemetry."""

    recorded_at: datetime
    simulated_elapsed_seconds: float
    metrics: FactoryMetrics
    scenario_id: str | None = None


class KpiSnapshotRepository(Protocol):
    async def insert(self, snapshot: KpiSnapshot) -> None: ...


class KpiSnapshotHistoryRepository(KpiSnapshotRepository, Protocol):

    async def list(
        self,
        *,
        start: datetime,
        end: datetime,
        scenario_id: str | None,
        limit: int,
        offset: int,
    ) -> list[KpiHistoryItem]: ...


class InMemoryKpiSnapshotRepository:
    def __init__(self) -> None:
        self.snapshots: list[KpiSnapshot] = []

    async def insert(self, snapshot: KpiSnapshot) -> None:
        self.snapshots.append(snapshot)

    async def list(
        self,
        *,
        start: datetime,
        end: datetime,
        scenario_id: str | None,
        limit: int,
        offset: int,
    ) -> list[KpiHistoryItem]:
        matches = sorted(
            (
                snapshot
                for snapshot in self.snapshots
                if start <= snapshot.recorded_at <= end
                and (scenario_id is None or snapshot.scenario_id == scenario_id)
            ),
            key=lambda snapshot: snapshot.recorded_at,
        )
        return [
            KpiHistoryItem(
                recorded_at=snapshot.recorded_at,
                simulated_elapsed_seconds=snapshot.simulated_elapsed_seconds,
                metrics=snapshot.metrics,
                scenario_id=snapshot.scenario_id,
            )
            for snapshot in matches[offset : offset + limit]
        ]


class SqlAlchemyKpiSnapshotRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def insert(self, snapshot: KpiSnapshot) -> None:
        metrics = snapshot.metrics
        async with self._database.session() as session:
            await session.execute(
                text(KPI_SNAPSHOT_INSERT_SQL),
                {
                    "scenario_id": snapshot.scenario_id,
                    "recorded_at": snapshot.recorded_at,
                    "simulated_elapsed_seconds": snapshot.simulated_elapsed_seconds,
                    "completed_tasks": metrics.completed_tasks,
                    "throughput_per_hour": metrics.throughput_per_hour,
                    "average_cycle_time_seconds": metrics.average_cycle_time_seconds,
                    "active_tasks": metrics.active_tasks,
                    "queued_tasks": metrics.queued_tasks,
                    "starvation_events": metrics.starvation_events,
                    "fleet_utilization_percent": metrics.fleet_utilization_percent,
                },
            )
            await session.commit()

    async def list(
        self,
        *,
        start: datetime,
        end: datetime,
        scenario_id: str | None,
        limit: int,
        offset: int,
    ) -> list[KpiHistoryItem]:
        async with self._database.session() as session:
            result = await session.execute(
                text("""
                    select scenario_id, recorded_at, simulated_elapsed_seconds,
                        completed_tasks, throughput_per_hour, average_cycle_time_seconds,
                        active_tasks, queued_tasks, starvation_events,
                        fleet_utilization_percent
                    from public.kpi_snapshots
                    where recorded_at between :start and :end
                      and (cast(:scenario_id as text) is null or scenario_id = :scenario_id)
                    order by recorded_at, id
                    limit :limit offset :offset
                """),
                {
                    "start": start,
                    "end": end,
                    "scenario_id": scenario_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            return [
                KpiHistoryItem(
                    recorded_at=row["recorded_at"],
                    simulated_elapsed_seconds=row["simulated_elapsed_seconds"],
                    scenario_id=row["scenario_id"],
                    metrics=FactoryMetrics(
                        completed_tasks=row["completed_tasks"],
                        throughput_per_hour=row["throughput_per_hour"],
                        average_cycle_time_seconds=row["average_cycle_time_seconds"],
                        active_tasks=row["active_tasks"],
                        queued_tasks=row["queued_tasks"],
                        starvation_events=row["starvation_events"],
                        fleet_utilization_percent=row["fleet_utilization_percent"],
                    ),
                )
                for row in result.mappings()
            ]


class KpiSnapshotWriter:
    """Persist downsampled KPI history on a wall-clock cadence.

    A single worker owns all inserts. If a write runs past a deadline, missed
    deadlines are skipped instead of starting overlapping writes or creating a
    catch-up burst. Database failures are isolated so the simulation and API
    remain available.
    """

    def __init__(
        self,
        *,
        repository: KpiSnapshotRepository,
        factory_state: FactoryState,
        simulated_elapsed_seconds: Callable[[], float],
        scenario_id: Callable[[], str | None] = lambda: None,
        interval_seconds: float = KPI_SNAPSHOT_INTERVAL_SECONDS,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("KPI snapshot interval must be positive")
        self._repository = repository
        self._factory_state = factory_state
        self._simulated_elapsed_seconds = simulated_elapsed_seconds
        self._scenario_id = scenario_id
        self._interval_seconds = interval_seconds
        self._monotonic = monotonic
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None
        self.running = False

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self.running = True
        self._task = asyncio.create_task(self._run(), name="kpi-snapshot-writer")
        logger.info("KPI snapshot writer started with %.1fs cadence", self._interval_seconds)

    async def stop(self) -> None:
        self.running = False
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        logger.info("KPI snapshot writer stopped")

    async def _run(self) -> None:
        monotonic = self._monotonic or asyncio.get_running_loop().time
        next_deadline = monotonic() + self._interval_seconds
        try:
            while self.running:
                await self._sleep(max(0.0, next_deadline - monotonic()))
                if not self.running:
                    break
                await self._write_once()

                next_deadline += self._interval_seconds
                now = monotonic()
                while next_deadline <= now:
                    next_deadline += self._interval_seconds
        finally:
            self.running = False

    async def _write_once(self) -> None:
        snapshot = KpiSnapshot(
            recorded_at=datetime.now(UTC),
            simulated_elapsed_seconds=max(0.0, self._simulated_elapsed_seconds()),
            metrics=self._factory_state.get_metrics(),
            scenario_id=self._scenario_id(),
        )
        try:
            await self._repository.insert(snapshot)
        except Exception:
            # Cancellation remains effective because asyncio.CancelledError is
            # a BaseException on supported Python versions.
            logger.exception("failed to persist KPI snapshot; writer will retry next cadence")


def build_kpi_snapshot_writer(
    *,
    database: Database,
    factory_state: FactoryState,
    simulated_elapsed_seconds: Callable[[], float],
) -> KpiSnapshotWriter | None:
    """Build the production writer only when durable storage is configured."""

    if not database.configured:
        return None
    return KpiSnapshotWriter(
        repository=SqlAlchemyKpiSnapshotRepository(database),
        factory_state=factory_state,
        simulated_elapsed_seconds=simulated_elapsed_seconds,
    )
