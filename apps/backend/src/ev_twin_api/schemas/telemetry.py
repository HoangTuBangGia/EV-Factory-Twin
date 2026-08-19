from enum import StrEnum

from pydantic import BaseModel
from twin_core.models.telemetry import RobotTelemetry

from ev_twin_api.schemas.base import UtcDatetime
from ev_twin_api.schemas.robot import Robot

__all__ = [
    "RobotTelemetry",
    "TelemetryIngressResponse",
    "TelemetryIngressStatus",
    "robot_to_telemetry",
]


class TelemetryIngressStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    IGNORED_STALE = "IGNORED_STALE"


class TelemetryIngressResponse(BaseModel):
    status: TelemetryIngressStatus
    robot_id: str
    source_timestamp: UtcDatetime
    ingested_at: UtcDatetime


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
