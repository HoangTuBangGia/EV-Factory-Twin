from pydantic import BaseModel, Field


class TelemetryRuntimeEvidence(BaseModel):
    received_total: int = Field(ge=0)
    accepted_total: int = Field(ge=0)
    ignored_stale_total: int = Field(ge=0)
    rejected_unknown_robot_total: int = Field(ge=0)
    rejected_future_timestamp_total: int = Field(ge=0)
    rejected_mock_active_total: int = Field(ge=0)
    persistence_submitted_total: int = Field(ge=0)
    persistence_coalesced_total: int = Field(ge=0)
    persisted_total: int = Field(ge=0)
    persistence_failures_total: int = Field(ge=0)
    persistence_pending_samples: int = Field(ge=0)
    websocket_broadcast_events_total: int = Field(ge=0)
    websocket_delivery_attempts_total: int = Field(ge=0)
    websocket_deliveries_total: int = Field(ge=0)
    websocket_delivery_failures_total: int = Field(ge=0)
    websocket_active_connections: int = Field(ge=0)
    latency_sample_count: int = Field(ge=0)
    source_to_ingest_latency_ms_p50: float | None = None
    source_to_ingest_latency_ms_p95: float | None = None
