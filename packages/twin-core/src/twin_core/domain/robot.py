from enum import StrEnum

from pydantic import BaseModel


class RobotStatus(StrEnum):
    IDLE = "IDLE"
    MOVING = "MOVING"
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
