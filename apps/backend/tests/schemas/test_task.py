from datetime import UTC, datetime

import pytest
from ev_twin_api.schemas.task import Task, TaskStatus
from pydantic import ValidationError


def test_task_status_has_seven_values() -> None:
    assert len(TaskStatus) == 7
    assert {status.value for status in TaskStatus} == {
        "QUEUED",
        "ASSIGNED",
        "PICKUP",
        "IN_PROGRESS",
        "DELIVERED",
        "COMPLETED",
        "FAILED",
    }


def test_task_defaults() -> None:
    task = Task(
        task_id="TASK-0001",
        payload_id="BP-0001",
        pickup="BATTERY_BUFFER",
        dropoff="MARRIAGE_STATION",
        status=TaskStatus.QUEUED,
        created_at=datetime.now(UTC),
    )
    assert task.type == "DELIVER_BATTERY"
    assert task.assigned_robot_id is None
    assert task.started_at is None
    assert task.completed_at is None


def test_task_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError):
        Task(
            payload_id="BP-0001",
            pickup="BATTERY_BUFFER",
            dropoff="MARRIAGE_STATION",
            status=TaskStatus.QUEUED,
            created_at=datetime.now(UTC),
        )  # type: ignore[call-arg]
