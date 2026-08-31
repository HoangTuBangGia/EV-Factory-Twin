from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from ev_twin_api.schemas.base import UtcDatetime


class TaskStatus(StrEnum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    PICKUP = "PICKUP"
    DELIVERING = "DELIVERING"
    TIMED_OUT = "TIMED_OUT"
    # Compatibility-only values for snapshots from before the MVP lifecycle was unified.
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


class CreateTransportTaskRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_-]*$")
    payload_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_-]*$")
    pickup_station_id: str = Field(min_length=1, max_length=100)
    dropoff_station_id: str = Field(min_length=1, max_length=100)
    navigation_timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=1, ge=0, le=5)

    @model_validator(mode="after")
    def stations_must_differ(self) -> "CreateTransportTaskRequest":
        if self.pickup_station_id == self.dropoff_station_id:
            raise ValueError("pickup and drop-off stations must differ")
        return self
