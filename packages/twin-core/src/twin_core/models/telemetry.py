from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer
from twin_core.domain.robot import Pose, RobotStatus, Velocity


def serialize_utc_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


UtcDatetime = Annotated[
    datetime,
    AfterValidator(validate_utc_datetime),
    PlainSerializer(serialize_utc_z, return_type=str, when_used="json"),
]


class RobotTelemetry(BaseModel):
    """Source-neutral realtime telemetry contract shared by MOCK, ROS, and REPLAY."""

    timestamp: UtcDatetime
    robot_id: str
    pose: Pose
    velocity: Velocity
    battery: float = Field(ge=0, le=100)
    status: RobotStatus
    task_id: str | None
    payload_id: str | None
