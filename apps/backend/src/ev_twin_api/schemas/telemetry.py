from pydantic import BaseModel, Field

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.robot import Pose, Robot, RobotStatus, Velocity


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


def robot_to_telemetry(robot: Robot) -> RobotTelemetry:
    return RobotTelemetry(
        timestamp=robot.last_seen_at,
        robot_id=robot.id,
        pose=robot.pose,
        velocity=robot.velocity,
        battery=robot.battery,
        status=robot.status,
        task_id=robot.task_id,
        payload_id=robot.payload_id,
    )
