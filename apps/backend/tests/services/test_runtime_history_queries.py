from datetime import UTC, datetime, timedelta

import pytest
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository


def telemetry(timestamp: datetime, *, robot_id: str = "AMR-01") -> RobotTelemetry:
    return RobotTelemetry.model_validate(
        {
            "timestamp": timestamp,
            "robot_id": robot_id,
            "pose": {"x": 1, "y": 2, "yaw": 0},
            "velocity": {"linear": 0.5, "angular": 0},
            "battery": 80,
            "status": "MOVING",
            "task_id": None,
            "payload_id": None,
        }
    )


@pytest.mark.asyncio
async def test_telemetry_history_filters_orders_limits_and_pages() -> None:
    repository = InMemoryRuntimeHistoryRepository()
    now = datetime.now(UTC)
    for seconds in (1, 2, 3):
        sample = telemetry(now + timedelta(seconds=seconds))
        await repository.record_telemetry(sample, sample.timestamp, TelemetryIngressStatus.ACCEPTED)
    other = telemetry(now + timedelta(seconds=4), robot_id="AMR-02")
    await repository.record_telemetry(other, other.timestamp, TelemetryIngressStatus.ACCEPTED)

    first_page = await repository.list_telemetry(
        robot_id="AMR-01",
        start=now,
        end=now + timedelta(seconds=5),
        before=None,
        limit=2,
    )
    second_page = await repository.list_telemetry(
        robot_id="AMR-01",
        start=now,
        end=now + timedelta(seconds=5),
        before=first_page[-1].telemetry.timestamp,
        limit=2,
    )

    assert [entry.telemetry.timestamp for entry in first_page] == [
        now + timedelta(seconds=3),
        now + timedelta(seconds=2),
    ]
    assert [entry.telemetry.timestamp for entry in second_page] == [now + timedelta(seconds=1)]
