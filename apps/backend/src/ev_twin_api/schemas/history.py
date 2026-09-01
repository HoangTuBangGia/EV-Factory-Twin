from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.edge_runtime import TaskUpdate
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus


class TelemetryHistoryItem(BaseModel):
    telemetry: RobotTelemetry
    ingested_at: UtcDatetime
    ordering_status: TelemetryIngressStatus


class TaskHistoryItem(BaseModel):
    update: TaskUpdate
    ingested_at: UtcDatetime


class KpiHistoryItem(BaseModel):
    recorded_at: UtcDatetime
    simulated_elapsed_seconds: float = Field(ge=0.0)
    metrics: FactoryMetrics
    scenario_id: str | None = None


class HistoryPage[HistoryItemT](BaseModel):
    items: list[HistoryItemT]
    next_offset: int | None = Field(default=None, ge=0)
