from enum import StrEnum

from pydantic import BaseModel

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


class FactoryAlert(BaseModel):
    id: str
    severity: AlertSeverity
    code: str
    message: str
    robot_id: str | None = None
    task_id: str | None = None
    timestamp: UtcDatetime
