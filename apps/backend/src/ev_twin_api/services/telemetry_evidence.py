from collections import deque
from datetime import datetime
from math import ceil

from ev_twin_api.schemas.runtime_evidence import TelemetryRuntimeEvidence


class TelemetryEvidence:
    """Bounded process-local evidence for the single-instance MVP runtime."""

    def __init__(self, *, latency_window_size: int = 10_000) -> None:
        if latency_window_size <= 0:
            raise ValueError("latency_window_size must be greater than zero")
        # ponytail: a bounded in-memory window is sufficient for one acceptance
        # run; use an external metrics backend before multi-instance deployment.
        self._latencies_ms: deque[float] = deque(maxlen=latency_window_size)
        self.received_total = 0
        self.accepted_total = 0
        self.ignored_stale_total = 0
        self.rejected_unknown_robot_total = 0
        self.rejected_future_timestamp_total = 0
        self.rejected_mock_active_total = 0
        self.persistence_submitted_total = 0
        self.persistence_coalesced_total = 0
        self.persisted_total = 0
        self.persistence_failures_total = 0
        self.websocket_broadcast_events_total = 0
        self.websocket_delivery_attempts_total = 0
        self.websocket_deliveries_total = 0
        self.websocket_delivery_failures_total = 0

    def record_received(self) -> None:
        self.received_total += 1

    def record_accepted(self, source_timestamp: datetime, ingested_at: datetime) -> None:
        self.accepted_total += 1
        self._latencies_ms.append((ingested_at - source_timestamp).total_seconds() * 1_000)

    def record_ignored_stale(self) -> None:
        self.ignored_stale_total += 1

    def record_rejected_unknown_robot(self) -> None:
        self.rejected_unknown_robot_total += 1

    def record_rejected_future_timestamp(self) -> None:
        self.rejected_future_timestamp_total += 1

    def record_rejected_mock_active(self) -> None:
        self.rejected_mock_active_total += 1

    def record_persistence_submission(self, *, coalesced: bool) -> None:
        self.persistence_submitted_total += 1
        self.persistence_coalesced_total += int(coalesced)

    def record_persisted(self) -> None:
        self.persisted_total += 1

    def record_persistence_failure(self) -> None:
        self.persistence_failures_total += 1

    def record_websocket_broadcast(
        self, *, delivery_attempts: int, deliveries: int, failures: int
    ) -> None:
        self.websocket_broadcast_events_total += 1
        self.websocket_delivery_attempts_total += delivery_attempts
        self.websocket_deliveries_total += deliveries
        self.websocket_delivery_failures_total += failures

    def snapshot(
        self, *, persistence_pending_samples: int, websocket_active_connections: int
    ) -> TelemetryRuntimeEvidence:
        ordered = sorted(self._latencies_ms)
        return TelemetryRuntimeEvidence(
            received_total=self.received_total,
            accepted_total=self.accepted_total,
            ignored_stale_total=self.ignored_stale_total,
            rejected_unknown_robot_total=self.rejected_unknown_robot_total,
            rejected_future_timestamp_total=self.rejected_future_timestamp_total,
            rejected_mock_active_total=self.rejected_mock_active_total,
            persistence_submitted_total=self.persistence_submitted_total,
            persistence_coalesced_total=self.persistence_coalesced_total,
            persisted_total=self.persisted_total,
            persistence_failures_total=self.persistence_failures_total,
            persistence_pending_samples=persistence_pending_samples,
            websocket_broadcast_events_total=self.websocket_broadcast_events_total,
            websocket_delivery_attempts_total=self.websocket_delivery_attempts_total,
            websocket_deliveries_total=self.websocket_deliveries_total,
            websocket_delivery_failures_total=self.websocket_delivery_failures_total,
            websocket_active_connections=websocket_active_connections,
            latency_sample_count=len(ordered),
            source_to_ingest_latency_ms_p50=self._percentile(ordered, 50),
            source_to_ingest_latency_ms_p95=self._percentile(ordered, 95),
        )

    @staticmethod
    def _percentile(ordered: list[float], percentile: int) -> float | None:
        if not ordered:
            return None
        return ordered[max(0, ceil(percentile / 100 * len(ordered)) - 1)]
