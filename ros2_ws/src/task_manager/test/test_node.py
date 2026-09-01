from collections import deque

from amr_interfaces.action import ExecuteTransportTask
from task_manager.node import (
    DEFAULT_NAVIGATION_TIMEOUT_SECONDS,
    TASK_STATUSES,
    TaskRecord,
    reserve_dispatch_batch,
    should_retry,
)


def test_task_statuses_match_mvp_lifecycle() -> None:
    assert {
        "QUEUED",
        "ASSIGNED",
        "PICKUP",
        "DELIVERING",
        "COMPLETED",
        "FAILED",
        "TIMED_OUT",
    } == TASK_STATUSES


def test_retry_is_bounded_and_only_for_execution_failures() -> None:
    assert should_retry(ExecuteTransportTask.Result.FAILED, 1, 1)
    assert should_retry(ExecuteTransportTask.Result.TIMED_OUT, 1, 2)
    assert not should_retry(ExecuteTransportTask.Result.FAILED, 2, 1)
    assert not should_retry(ExecuteTransportTask.Result.SUCCESS, 1, 2)
    assert not should_retry(ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE, 1, 2)


def test_dispatch_reserves_one_task_per_available_robot_concurrently() -> None:
    tasks = {
        task_id: TaskRecord(task_id, f"BP-{index}", "BUFFER", "LINE", 120.0, 1)
        for index, task_id in enumerate(("TASK-1", "TASK-2", "TASK-3"), start=1)
    }
    queue = deque(tasks)
    active = set()

    first = reserve_dispatch_batch(queue, tasks, active, max_concurrent_tasks=2)

    assert [task.task_id for task in first] == ["TASK-1", "TASK-2"]
    assert active == {"TASK-1", "TASK-2"}
    assert list(queue) == ["TASK-3"]
    assert all(task.attempt == 1 for task in first)
    assert reserve_dispatch_batch(queue, tasks, active, max_concurrent_tasks=2) == []

    active.remove("TASK-1")
    assert [
        task.task_id
        for task in reserve_dispatch_batch(queue, tasks, active, max_concurrent_tasks=2)
    ] == ["TASK-3"]


def test_default_navigation_timeout_covers_the_production_route() -> None:
    assert DEFAULT_NAVIGATION_TIMEOUT_SECONDS == 120.0
