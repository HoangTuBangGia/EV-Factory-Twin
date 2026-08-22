from amr_interfaces.action import ExecuteTransportTask
from task_manager.node import TASK_STATUSES, should_retry


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
