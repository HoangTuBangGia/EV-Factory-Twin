from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from twin_core.models.telemetry import RobotTelemetry


def test_robot_telemetry_is_source_neutral_and_serializes_utc() -> None:
    telemetry = RobotTelemetry(
        timestamp=datetime(2026, 8, 11, 4, 0, 0, 125000, tzinfo=UTC),
        robot_id="AMR-01",
        pose={"x": 12.4, "y": 7.8, "yaw": 1.57},
        velocity={"linear": 1.1, "angular": 0.0},
        battery=82.4,
        status="DELIVERING",
        task_id="TASK-0102",
        payload_id="BP-0102",
    )

    assert telemetry.model_dump(mode="json") == {
        "timestamp": "2026-08-11T04:00:00.125Z",
        "robot_id": "AMR-01",
        "pose": {"x": 12.4, "y": 7.8, "yaw": 1.57},
        "velocity": {"linear": 1.1, "angular": 0.0},
        "battery": 82.4,
        "status": "DELIVERING",
        "task_id": "TASK-0102",
        "payload_id": "BP-0102",
    }


@pytest.mark.parametrize("battery", [-0.1, 100.1])
def test_robot_telemetry_rejects_invalid_battery(battery: float) -> None:
    with pytest.raises(ValidationError):
        RobotTelemetry.model_validate(
            {
                "timestamp": "2026-08-11T04:00:00.125Z",
                "robot_id": "AMR-01",
                "pose": {"x": 0, "y": 0, "yaw": 0},
                "velocity": {"linear": 0, "angular": 0},
                "battery": battery,
                "status": "IDLE",
                "task_id": None,
                "payload_id": None,
            }
        )
