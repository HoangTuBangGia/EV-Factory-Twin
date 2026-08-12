from datetime import UTC, datetime

import pytest
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.telemetry import RobotTelemetry
from pydantic import ValidationError

SAMPLE_JSON = {
    "timestamp": "2026-08-11T04:00:00.125Z",
    "robot_id": "AMR-01",
    "pose": {"x": 12.4, "y": 7.8, "yaw": 1.57},
    "velocity": {"linear": 1.1, "angular": 0.0},
    "battery": 82.4,
    "status": "DELIVERING",
    "task_id": "TASK-0102",
    "payload_id": "BP-0102",
}


def test_telemetry_serializes_to_sample_json() -> None:
    telemetry = RobotTelemetry(
        timestamp=datetime(2026, 8, 11, 4, 0, 0, 125000, tzinfo=UTC),
        robot_id="AMR-01",
        pose={"x": 12.4, "y": 7.8, "yaw": 1.57},  # type: ignore[arg-type]
        velocity={"linear": 1.1, "angular": 0.0},  # type: ignore[arg-type]
        battery=82.4,
        status=RobotStatus.DELIVERING,
        task_id="TASK-0102",
        payload_id="BP-0102",
    )

    assert telemetry.model_dump(mode="json") == SAMPLE_JSON


def test_telemetry_round_trips_from_sample_json() -> None:
    telemetry = RobotTelemetry.model_validate(SAMPLE_JSON)

    assert telemetry.robot_id == "AMR-01"
    assert telemetry.model_dump(mode="json") == SAMPLE_JSON


@pytest.mark.parametrize("battery", [-1.0, 101.0])
def test_telemetry_battery_out_of_range_raises(battery: float) -> None:
    payload = {**SAMPLE_JSON, "battery": battery}
    with pytest.raises(ValidationError):
        RobotTelemetry.model_validate(payload)


def test_telemetry_task_and_payload_accept_explicit_none() -> None:
    payload = {**SAMPLE_JSON, "task_id": None, "payload_id": None}
    telemetry = RobotTelemetry.model_validate(payload)
    assert telemetry.task_id is None
    assert telemetry.payload_id is None


def test_telemetry_task_id_is_required_even_though_nullable() -> None:
    payload = {k: v for k, v in SAMPLE_JSON.items() if k != "task_id"}
    with pytest.raises(ValidationError):
        RobotTelemetry.model_validate(payload)
