from enum import StrEnum

from pydantic import BaseModel

from ev_twin_api.schemas.base import UtcDatetime


class TaskStatus(StrEnum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    PICKUP = "PICKUP"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(BaseModel):
    task_id: str
    type: str = "DELIVER_BATTERY"
    payload_id: str
    pickup: str
    dropoff: str
    assigned_robot_id: str | None = None
    status: TaskStatus
    created_at: UtcDatetime
    started_at: UtcDatetime | None = None
    completed_at: UtcDatetime | None = None
