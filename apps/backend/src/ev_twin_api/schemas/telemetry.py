from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.robot import Pose, RobotStatus, Velocity


class RobotTelemetry(BaseModel):
    """The FE-BE realtime contract. Field names/units are frozen once frontend
    integration begins — do not rename casually."""

    timestamp: UtcDatetime
    robot_id: str
    pose: Pose
    velocity: Velocity
    battery: float = Field(ge=0, le=100)
    status: RobotStatus
    task_id: str | None
    payload_id: str | None
