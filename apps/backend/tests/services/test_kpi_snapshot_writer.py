import asyncio
import logging

import pytest
from ev_twin_api.core.database import Database
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.kpi_snapshot_writer import (
    KPI_SNAPSHOT_INTERVAL_SECONDS,
    KpiSnapshot,
    KpiSnapshotWriter,
    build_kpi_snapshot_writer,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleep_delays: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleep_delays.append(delay)
        self.now += delay
        await asyncio.sleep(0)


class RecordingRepository:
    def __init__(self, *, target_count: int = 1, clock: FakeClock | None = None) -> None:
        self.snapshots: list[KpiSnapshot] = []
        self.target_count = target_count
        self.clock = clock
        self.ready = asyncio.Event()
        self.active_writes = 0
        self.max_active_writes = 0

    async def insert(self, snapshot: KpiSnapshot) -> None:
        self.active_writes += 1
        self.max_active_writes = max(self.max_active_writes, self.active_writes)
        try:
            self.snapshots.append(snapshot)
            if self.clock is not None and len(self.snapshots) == 1:
                # Model a 25-second insert. The writer must skip the elapsed
                # 20s and 30s deadlines rather than create overlapping work.
                self.clock.now += 25.0
            await asyncio.sleep(0)
            if len(self.snapshots) >= self.target_count:
                self.ready.set()
        finally:
            self.active_writes -= 1


def make_state() -> FactoryState:
    state = FactoryState(MockFactoryConfig())
    state.update_metrics(
        FactoryMetrics(
            completed_tasks=7,
            throughput_per_hour=42.0,
            average_cycle_time_seconds=18.5,
            active_tasks=2,
            queued_tasks=3,
            starvation_events=1,
            fleet_utilization_percent=60.0,
        )
    )
    return state


@pytest.mark.asyncio
async def test_writer_uses_wall_clock_cadence_without_overlapping_catch_up() -> None:
    clock = FakeClock()
    repository = RecordingRepository(target_count=2, clock=clock)
    writer = KpiSnapshotWriter(
        repository=repository,
        factory_state=make_state(),
        simulated_elapsed_seconds=lambda: 123.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    await writer.start()
    await asyncio.wait_for(repository.ready.wait(), timeout=1.0)
    await writer.stop()

    assert clock.sleep_delays[:2] == [KPI_SNAPSHOT_INTERVAL_SECONDS, 5.0]
    assert repository.max_active_writes == 1
    assert repository.snapshots[0].scenario_id is None
    assert repository.snapshots[0].simulated_elapsed_seconds == 123.0
    assert repository.snapshots[0].metrics.completed_tasks == 7


@pytest.mark.asyncio
async def test_database_error_is_logged_and_next_snapshot_is_still_written(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = FakeClock()
    succeeded = asyncio.Event()

    class FailOnceRepository:
        def __init__(self) -> None:
            self.calls = 0

        async def insert(self, snapshot: KpiSnapshot) -> None:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("database unavailable")
            succeeded.set()

    repository = FailOnceRepository()
    writer = KpiSnapshotWriter(
        repository=repository,
        factory_state=make_state(),
        simulated_elapsed_seconds=lambda: 5.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with caplog.at_level(logging.ERROR, logger="ev_twin_api"):
        await writer.start()
        await asyncio.wait_for(succeeded.wait(), timeout=1.0)
        await writer.stop()

    assert repository.calls >= 2
    assert "failed to persist KPI snapshot" in caplog.text
    assert writer.running is False


@pytest.mark.asyncio
async def test_stop_cancels_an_in_flight_write_and_leaves_no_worker() -> None:
    clock = FakeClock()
    entered = asyncio.Event()
    cancelled = asyncio.Event()
    never_finishes = asyncio.Event()

    class BlockingRepository:
        async def insert(self, snapshot: KpiSnapshot) -> None:
            entered.set()
            try:
                await never_finishes.wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    writer = KpiSnapshotWriter(
        repository=BlockingRepository(),
        factory_state=make_state(),
        simulated_elapsed_seconds=lambda: 0.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    await writer.start()
    await asyncio.wait_for(entered.wait(), timeout=1.0)
    await writer.stop()

    assert cancelled.is_set()
    assert writer.running is False
    assert writer._task is None


@pytest.mark.asyncio
async def test_writer_is_built_only_for_a_configured_database() -> None:
    state = make_state()
    unconfigured = Database(None)
    configured = Database(
        "postgresql://user:password@127.0.0.1:5432/factory",
        ssl_mode="disable",
    )

    assert (
        build_kpi_snapshot_writer(
            database=unconfigured,
            factory_state=state,
            simulated_elapsed_seconds=lambda: 0.0,
        )
        is None
    )
    assert (
        build_kpi_snapshot_writer(
            database=configured,
            factory_state=state,
            simulated_elapsed_seconds=lambda: 0.0,
        )
        is not None
    )

    await configured.dispose()


def test_writer_rejects_non_positive_cadence() -> None:
    with pytest.raises(ValueError, match="interval must be positive"):
        KpiSnapshotWriter(
            repository=RecordingRepository(),
            factory_state=make_state(),
            simulated_elapsed_seconds=lambda: 0.0,
            interval_seconds=0.0,
        )
