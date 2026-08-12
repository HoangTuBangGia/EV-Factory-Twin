from datetime import UTC, datetime

import pytest
from ev_twin_api.schemas.robot import Pose, Robot, RobotStatus, Velocity
from pydantic import ValidationError


def test_robot_status_has_ten_values() -> None:
    assert len(RobotStatus) == 10
    assert {status.value for status in RobotStatus} == {
        "IDLE",
        "MOVING_TO_PICKUP",
        "PICKING",
        "DELIVERING",
        "DROPPING",
        "MOVING_TO_CHARGER",
        "WAITING",
        "CHARGING",
        "ERROR",
        "OFFLINE",
    }


def _make_robot(**overrides: object) -> Robot:
    defaults: dict[str, object] = {
        "id": "AMR-01",
        "name": "AMR-01",
        "status": RobotStatus.IDLE,
        "pose": Pose(x=5.0, y=12.0, yaw=0.0),
        "velocity": Velocity(linear=0.0, angular=0.0),
        "battery": 100.0,
        "last_seen_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Robot(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize("battery", [0.0, 100.0])
def test_robot_battery_boundaries_are_valid(battery: float) -> None:
    robot = _make_robot(battery=battery)
    assert robot.battery == battery


@pytest.mark.parametrize("battery", [-1.0, 101.0])
def test_robot_battery_out_of_range_raises(battery: float) -> None:
    with pytest.raises(ValidationError):
        _make_robot(battery=battery)


def test_robot_task_and_payload_default_to_none() -> None:
    robot = _make_robot()
    assert robot.task_id is None
    assert robot.payload_id is None


def test_robot_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError):
        Robot(
            name="AMR-01",
            status=RobotStatus.IDLE,
            pose=Pose(x=0, y=0, yaw=0),
            velocity=Velocity(linear=0, angular=0),
            battery=100.0,
            last_seen_at=datetime.now(UTC),
        )  # type: ignore[call-arg]
