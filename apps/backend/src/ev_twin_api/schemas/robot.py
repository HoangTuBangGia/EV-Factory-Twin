from pydantic import BaseModel, Field
from twin_core.domain.robot import Pose, RobotStatus, Velocity

from ev_twin_api.schemas.base import UtcDatetime

__all__ = ["Pose", "Robot", "RobotStatus", "Velocity"]


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
