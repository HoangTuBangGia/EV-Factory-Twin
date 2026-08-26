from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository
from ev_twin_api.services.telemetry_evidence import TelemetryEvidence
from ev_twin_api.services.telemetry_persistence import TelemetryPersistenceWorker


def telemetry(timestamp: datetime, battery: float) -> RobotTelemetry:
    return RobotTelemetry.model_validate(
        {
            "timestamp": timestamp,
            "robot_id": "AMR-01",
            "pose": {"x": 1, "y": 2, "yaw": 0},
            "velocity": {"linear": 0.5, "angular": 0},
            "battery": battery,
            "status": "MOVING",
            "task_id": None,
            "payload_id": None,
        }
    )


@pytest.mark.asyncio
async def test_worker_coalesces_latest_sample_per_robot_and_ordering_class() -> None:
    repository = InMemoryRuntimeHistoryRepository()
    evidence = TelemetryEvidence()
    worker = TelemetryPersistenceWorker(repository, None, flush_seconds=1, evidence=evidence)
    now = datetime.now(UTC)

    worker.submit(telemetry(now, 90), now, TelemetryIngressStatus.ACCEPTED)
    worker.submit(
        telemetry(now + timedelta(milliseconds=100), 89),
        now,
        TelemetryIngressStatus.ACCEPTED,
    )
    worker.submit(
        telemetry(now - timedelta(seconds=1), 91),
        now,
        TelemetryIngressStatus.IGNORED_STALE,
    )
    await worker.flush()

    assert [(item.battery, status) for item, _, status in repository.telemetry] == [
        (89, TelemetryIngressStatus.ACCEPTED),
        (91, TelemetryIngressStatus.IGNORED_STALE),
    ]
    snapshot = evidence.snapshot(
        persistence_pending_samples=worker.pending_count,
        websocket_active_connections=0,
    )
    assert snapshot.persistence_submitted_total == 3
    assert snapshot.persistence_coalesced_total == 1
    assert snapshot.persisted_total == 2
    assert snapshot.persistence_pending_samples == 0


@pytest.mark.asyncio
async def test_worker_retries_failed_latest_sample() -> None:
    class FlakyRepository(InMemoryRuntimeHistoryRepository):
        attempts = 0

        async def record_telemetry(self, telemetry, ingested_at, ordering_status):
            self.attempts += 1
            if self.attempts == 1:
                raise ConnectionError("database unavailable")
            await super().record_telemetry(telemetry, ingested_at, ordering_status)

    repository = FlakyRepository()
    evidence = TelemetryEvidence()
    worker = TelemetryPersistenceWorker(repository, None, flush_seconds=1, evidence=evidence)
    now = datetime.now(UTC)
    worker.submit(telemetry(now, 90), now, TelemetryIngressStatus.ACCEPTED)

    await worker.flush()
    assert repository.telemetry == []
    await worker.flush()

    assert repository.attempts == 2
    assert repository.telemetry[0][0].battery == 90
    snapshot = evidence.snapshot(
        persistence_pending_samples=worker.pending_count,
        websocket_active_connections=0,
    )
    assert snapshot.persistence_failures_total == 1
    assert snapshot.persisted_total == 1


@pytest.mark.asyncio
async def test_history_failure_does_not_hide_live_telemetry_from_health() -> None:
    repository = InMemoryRuntimeHistoryRepository()
    repository.record_telemetry = AsyncMock(side_effect=ConnectionError("database unavailable"))
    runtime_health = AsyncMock()
    worker = TelemetryPersistenceWorker(repository, runtime_health, flush_seconds=1)
    now = datetime.now(UTC)
    sample = telemetry(now, 90)
    worker.submit(sample, now, TelemetryIngressStatus.ACCEPTED)

    await worker.flush()

    runtime_health.note_telemetry.assert_awaited_once_with(sample, now)
