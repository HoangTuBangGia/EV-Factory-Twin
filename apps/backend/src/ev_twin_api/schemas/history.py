from typing import Self

from pydantic import BaseModel, Field, model_validator

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus


class HistoryQuery(BaseModel):
    start: UtcDatetime
    end: UtcDatetime
    before: UtcDatetime | None = None
    limit: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start > self.end:
            raise ValueError("start must not be after end")
        if self.before is not None and not self.start < self.before <= self.end:
            raise ValueError("before must be after start and no later than end")
        return self


class AuditHistoryQuery(HistoryQuery):
    before_id: int | None = Field(default=None, ge=1)
    resource_type: str | None = Field(default=None, min_length=1, max_length=100)
    resource_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_audit_cursor(self) -> Self:
        if (self.before is None) != (self.before_id is None):
            raise ValueError("before and before_id must be provided together")
        return self


class TelemetryHistoryEntry(BaseModel):
    telemetry: RobotTelemetry
    ingested_at: UtcDatetime
    ordering_status: TelemetryIngressStatus
