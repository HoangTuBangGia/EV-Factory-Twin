from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.command import Command
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry


class WebSocketEventType(StrEnum):
    AUTH_OK = "auth.ok"
    ROBOT_TELEMETRY = "robot.telemetry"
    TASK_UPDATED = "task.updated"
    METRICS_UPDATED = "metrics.updated"
    ALERT_CREATED = "alert.created"
    FACTORY_RESET = "factory.reset"
    COMMAND_UPDATED = "command.updated"


class WebSocketEvent(BaseModel):
    """The `/ws/factory` envelope shape. Used for validating event shape in
    tests; broadcast payloads are built as plain dicts (see the `*_event`
    functions below) so each event's own field serializers apply reliably."""

    type: WebSocketEventType
    data: Any


class WebSocketAuthMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["auth"]
    access_token: str = Field(min_length=1, max_length=8192)


class WebSocketAuthOkData(BaseModel):
    user_id: UUID
    display_name: str
    role: AppRole
    expires_at: int


def auth_ok_event(data: WebSocketAuthOkData) -> dict[str, Any]:
    return {"type": WebSocketEventType.AUTH_OK, "data": data.model_dump(mode="json")}


def robot_telemetry_event(telemetry: RobotTelemetry) -> dict[str, Any]:
    return {"type": WebSocketEventType.ROBOT_TELEMETRY, "data": telemetry.model_dump(mode="json")}


def task_updated_event(task: Task) -> dict[str, Any]:
    return {"type": WebSocketEventType.TASK_UPDATED, "data": task.model_dump(mode="json")}


def metrics_updated_event(metrics: FactoryMetrics) -> dict[str, Any]:
    return {"type": WebSocketEventType.METRICS_UPDATED, "data": metrics.model_dump(mode="json")}


def alert_created_event(alert: FactoryAlert) -> dict[str, Any]:
    return {"type": WebSocketEventType.ALERT_CREATED, "data": alert.model_dump(mode="json")}


def factory_reset_event() -> dict[str, Any]:
    return {"type": WebSocketEventType.FACTORY_RESET, "data": None}


def command_updated_event(command: Command) -> dict[str, Any]:
    return {"type": WebSocketEventType.COMMAND_UPDATED, "data": command.model_dump(mode="json")}
