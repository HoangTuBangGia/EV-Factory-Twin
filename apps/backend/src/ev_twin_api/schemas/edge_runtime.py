from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

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

    @field_validator("robot_ids")
    @classmethod
    def validate_robot_ids(cls, robot_ids: list[str]) -> list[str]:
        if any(not robot_id.strip() or len(robot_id) > 100 for robot_id in robot_ids):
            raise ValueError("robot IDs must contain 1 to 100 non-whitespace characters")
        if len(set(robot_ids)) != len(robot_ids):
            raise ValueError("robot IDs must be unique")
        return robot_ids


class EdgeUpdateResponse(BaseModel):
    accepted: bool
    identifier: str
