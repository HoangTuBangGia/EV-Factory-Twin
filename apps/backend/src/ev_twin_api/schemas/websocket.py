from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry


class WebSocketEventType(StrEnum):
    ROBOT_TELEMETRY = "robot.telemetry"
    TASK_UPDATED = "task.updated"
    METRICS_UPDATED = "metrics.updated"
    ALERT_CREATED = "alert.created"
    FACTORY_RESET = "factory.reset"


class WebSocketEvent(BaseModel):
    """The `/ws/factory` envelope shape. Used for validating event shape in
    tests; broadcast payloads are built as plain dicts (see the `*_event`
    functions below) so each event's own field serializers apply reliably."""

    type: WebSocketEventType
    data: Any


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
