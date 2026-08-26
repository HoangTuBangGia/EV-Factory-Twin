from datetime import UTC, datetime, timedelta

import pytest
from ev_twin_api.services.telemetry_evidence import TelemetryEvidence


def test_evidence_reports_bounded_nearest_rank_latency_percentiles() -> None:
    evidence = TelemetryEvidence(latency_window_size=3)
    ingested_at = datetime.now(UTC)
    for latency_ms in (10, 20, 30, 40):
        evidence.record_received()
        evidence.record_accepted(ingested_at - timedelta(milliseconds=latency_ms), ingested_at)

    snapshot = evidence.snapshot(
        persistence_pending_samples=2,
        websocket_active_connections=1,
    )

    assert snapshot.received_total == 4
    assert snapshot.accepted_total == 4
    assert snapshot.latency_sample_count == 3
    assert snapshot.source_to_ingest_latency_ms_p50 == pytest.approx(30)
    assert snapshot.source_to_ingest_latency_ms_p95 == pytest.approx(40)
    assert snapshot.persistence_pending_samples == 2
    assert snapshot.websocket_active_connections == 1


def test_evidence_counts_rejections_persistence_and_websocket_delivery() -> None:
    evidence = TelemetryEvidence()
    evidence.record_ignored_stale()
    evidence.record_rejected_unknown_robot()
    evidence.record_rejected_future_timestamp()
    evidence.record_rejected_mock_active()
    evidence.record_persistence_submission(coalesced=False)
    evidence.record_persistence_submission(coalesced=True)
    evidence.record_persisted()
    evidence.record_persistence_failure()
    evidence.record_websocket_broadcast(delivery_attempts=2, deliveries=1, failures=1)

    snapshot = evidence.snapshot(
        persistence_pending_samples=0,
        websocket_active_connections=1,
    )

    assert snapshot.ignored_stale_total == 1
    assert snapshot.rejected_unknown_robot_total == 1
    assert snapshot.rejected_future_timestamp_total == 1
    assert snapshot.rejected_mock_active_total == 1
    assert snapshot.persistence_submitted_total == 2
    assert snapshot.persistence_coalesced_total == 1
    assert snapshot.persisted_total == 1
    assert snapshot.persistence_failures_total == 1
    assert snapshot.websocket_broadcast_events_total == 1
    assert snapshot.websocket_delivery_attempts_total == 2
    assert snapshot.websocket_deliveries_total == 1
    assert snapshot.websocket_delivery_failures_total == 1
