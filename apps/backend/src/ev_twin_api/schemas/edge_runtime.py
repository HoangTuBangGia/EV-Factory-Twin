from enum import StrEnum

from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.task import TaskStatus


class TaskUpdate(BaseModel):
    task_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    pickup_station_id: str = Field(min_length=1)
    dropoff_station_id: str = Field(min_length=1)
    assigned_robot_id: str | None = None
    status: TaskStatus
    attempt: int = Field(ge=0)
    max_retries: int = Field(ge=0)
    message: str = ""
    updated_at: UtcDatetime


class BridgeStatus(StrEnum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"


class BridgeHealth(BaseModel):
    bridge_id: str = Field(min_length=1)
    status: BridgeStatus
    robot_ids: list[str] = Field(min_length=1)
    timestamp: UtcDatetime
    delivered_samples: int = Field(ge=0)
    failed_deliveries: int = Field(ge=0)
    last_error: str | None = None


class EdgeUpdateResponse(BaseModel):
    accepted: bool
    identifier: str
