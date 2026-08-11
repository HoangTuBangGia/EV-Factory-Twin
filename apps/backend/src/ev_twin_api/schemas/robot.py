from enum import StrEnum

from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime


class RobotStatus(StrEnum):
    IDLE = "IDLE"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    PICKING = "PICKING"
    DELIVERING = "DELIVERING"
    DROPPING = "DROPPING"
    MOVING_TO_CHARGER = "MOVING_TO_CHARGER"
    WAITING = "WAITING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class Pose(BaseModel):
    x: float
    y: float
    yaw: float


class Velocity(BaseModel):
    linear: float
    angular: float


class Robot(BaseModel):
    id: str
    name: str
    status: RobotStatus
    pose: Pose
    velocity: Velocity
    battery: float = Field(ge=0, le=100)
    task_id: str | None = None
    payload_id: str | None = None
    last_seen_at: UtcDatetime
