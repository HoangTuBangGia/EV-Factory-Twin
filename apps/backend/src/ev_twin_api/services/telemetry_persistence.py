import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime

from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import RuntimeHistoryRepository
from ev_twin_api.services.telemetry_evidence import TelemetryEvidence

logger = logging.getLogger("ev_twin_api")


@dataclass(frozen=True)
class PendingTelemetry:
    telemetry: RobotTelemetry
    ingested_at: datetime
    ordering_status: TelemetryIngressStatus


class TelemetryPersistenceWorker:
    """Persist bounded latest telemetry without blocking realtime ingress."""

    def __init__(
        self,
        history: RuntimeHistoryRepository,
        runtime_health: RuntimeHealthService | None,
        *,
        flush_seconds: float,
        evidence: TelemetryEvidence | None = None,
    ) -> None:
        self._history = history
        self._runtime_health = runtime_health
        self._flush_seconds = flush_seconds
        self._evidence = evidence or TelemetryEvidence()
        self._pending: dict[tuple[str, TelemetryIngressStatus], PendingTelemetry] = {}
        self._task: asyncio.Task[None] | None = None

    def submit(
        self,
        telemetry: RobotTelemetry,
        ingested_at: datetime,
        ordering_status: TelemetryIngressStatus,
    ) -> None:
        key = (telemetry.robot_id, ordering_status)
        current = self._pending.get(key)
        self._evidence.record_persistence_submission(coalesced=current is not None)
        if current is None or telemetry.timestamp > current.telemetry.timestamp:
            self._pending[key] = PendingTelemetry(
                telemetry.model_copy(deep=True), ingested_at, ordering_status
            )

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="telemetry-persistence")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        try:
            await asyncio.wait_for(self.flush(), timeout=5.0)
        except TimeoutError:
            logger.warning("telemetry persistence shutdown flush timed out")

    async def flush(self) -> None:
        batch, self._pending = self._pending, {}
        if batch:
            await asyncio.gather(*(self._persist(key, item) for key, item in batch.items()))

    async def _persist(
        self,
        key: tuple[str, TelemetryIngressStatus],
        item: PendingTelemetry,
    ) -> None:
        try:
            if (
                item.ordering_status == TelemetryIngressStatus.ACCEPTED
                and self._runtime_health is not None
            ):
                await self._runtime_health.note_telemetry(item.telemetry, item.ingested_at)
            await self._history.record_telemetry(
                item.telemetry, item.ingested_at, item.ordering_status
            )
            self._evidence.record_persisted()
        except Exception:
            self._evidence.record_persistence_failure()
            current = self._pending.get(key)
            if current is None or item.telemetry.timestamp > current.telemetry.timestamp:
                self._pending[key] = item
            logger.exception("telemetry persistence failed; retained latest sample")

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._flush_seconds)
            await self.flush()
