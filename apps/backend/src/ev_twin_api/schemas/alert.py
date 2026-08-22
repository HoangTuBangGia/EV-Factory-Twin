from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ev_twin_api.schemas.base import UtcDatetime


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertCode(StrEnum):
    LOW_BATTERY = "LOW_BATTERY"
    ROBOT_WAITING = "ROBOT_WAITING"
    TASK_BACKLOG = "TASK_BACKLOG"
    STARVATION = "STARVATION"
    ROBOT_ERROR = "ROBOT_ERROR"
    STALE_TELEMETRY = "STALE_TELEMETRY"
    BRIDGE_DISCONNECTED = "BRIDGE_DISCONNECTED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    CONGESTION = "CONGESTION"


class AlertStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLEARED = "CLEARED"


class FactoryAlert(BaseModel):
    id: UUID
    dedupe_key: str = Field(min_length=1, max_length=200)
    severity: AlertSeverity
    code: AlertCode
    status: AlertStatus = AlertStatus.ACTIVE
    message: str = Field(min_length=1, max_length=1000)
    robot_id: str | None = None
    task_id: str | None = None
    operation_id: UUID | None = None
    timestamp: UtcDatetime
    last_seen_at: UtcDatetime | None = None
    cleared_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "FactoryAlert":
        if self.last_seen_at is None:
            self.last_seen_at = self.timestamp
        if self.status == AlertStatus.ACTIVE and self.cleared_at is not None:
            raise ValueError("active alert cannot have cleared_at")
        if self.status == AlertStatus.CLEARED:
            if self.cleared_at is None:
                raise ValueError("cleared alert requires cleared_at")
            if self.cleared_at < self.timestamp:
                raise ValueError("cleared_at cannot precede timestamp")
        return self
