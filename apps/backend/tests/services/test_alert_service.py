from datetime import UTC, datetime, timedelta

from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.alert_service import (
    LOW_BATTERY,
    ROBOT_WAITING,
    STARVATION,
    TASK_BACKLOG,
    AlertService,
)
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.metrics_service import STARVATION_THRESHOLD_SECONDS


def _new_state(robot_count: int = 1) -> FactoryState:
    return FactoryState(config=MockFactoryConfig(robot_count=robot_count))


def _set_battery(state: FactoryState, robot_id: str, battery: float) -> None:
    robot = state.get_robot(robot_id)
    assert robot is not None
    robot.battery = battery
    state.update_robot(robot)


def _queued_task(task_id: str, *, created_at: datetime | None = None) -> Task:
    return Task(
        task_id=task_id,
        payload_id=f"BP-{task_id}",
        pickup="BATTERY_BUFFER",
        dropoff="MARRIAGE_STATION",
        status=TaskStatus.QUEUED,
        created_at=created_at or datetime.now(UTC),
    )


def test_low_battery_crossing_below_threshold_creates_exactly_one_alert() -> None:
    state = _new_state()
    service = AlertService(state)
    _set_battery(state, "AMR-01", 15.0)

    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert len(alerts) == 1
    assert alerts[0].code == LOW_BATTERY
    assert alerts[0].robot_id == "AMR-01"
    assert alerts[0].severity == "WARNING"


def test_low_battery_remaining_below_threshold_does_not_flood() -> None:
    state = _new_state()
    service = AlertService(state)
    _set_battery(state, "AMR-01", 15.0)

    first = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    third = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert len(first) == 1
    assert second == []
    assert third == []


def test_low_battery_recovering_then_falling_again_creates_a_new_alert() -> None:
    state = _new_state()
    service = AlertService(state)
    _set_battery(state, "AMR-01", 15.0)
    first = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    assert len(first) == 1

    _set_battery(state, "AMR-01", 90.0)
    recovered = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    assert recovered == []

    _set_battery(state, "AMR-01", 10.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert len(second) == 1
    assert second[0].code == LOW_BATTERY
    assert second[0].id != first[0].id


def test_alert_ids_are_sequential() -> None:
    state = _new_state(robot_count=2)
    service = AlertService(state)
    _set_battery(state, "AMR-01", 5.0)
    _set_battery(state, "AMR-02", 5.0)

    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert {alert.id for alert in alerts} == {"ALERT-0001", "ALERT-0002"}


def test_task_backlog_fires_when_queued_exceeds_robot_count() -> None:
    state = _new_state(robot_count=2)
    service = AlertService(state)
    for i in range(1, 4):  # 3 queued tasks > 2 robots
        state.add_task(_queued_task(f"TASK-000{i}"))

    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    backlog_alerts = [alert for alert in alerts if alert.code == TASK_BACKLOG]
    assert len(backlog_alerts) == 1


def test_task_backlog_does_not_flood_while_condition_persists() -> None:
    state = _new_state(robot_count=1)
    service = AlertService(state)
    state.add_task(_queued_task("TASK-0001"))
    state.add_task(_queued_task("TASK-0002"))

    first = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert len([alert for alert in first if alert.code == TASK_BACKLOG]) == 1
    assert len([alert for alert in second if alert.code == TASK_BACKLOG]) == 0


def test_task_backlog_clears_and_can_retrigger_once_below_threshold() -> None:
    state = _new_state(robot_count=1)
    service = AlertService(state)
    task = _queued_task("TASK-0001")
    state.add_task(task)
    state.add_task(_queued_task("TASK-0002"))
    first = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    assert len([alert for alert in first if alert.code == TASK_BACKLOG]) == 1

    assigned = task.model_copy(update={"status": TaskStatus.ASSIGNED})
    state.update_task(assigned)
    cleared = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    assert [alert for alert in cleared if alert.code == TASK_BACKLOG] == []

    state.add_task(_queued_task("TASK-0003"))
    state.add_task(_queued_task("TASK-0004"))
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    assert len([alert for alert in second if alert.code == TASK_BACKLOG]) == 1


def test_starvation_alert_fires_once_for_task_queued_past_threshold() -> None:
    state = _new_state()
    service = AlertService(state)
    stale_created_at = datetime.now(UTC) - timedelta(seconds=STARVATION_THRESHOLD_SECONDS + 1)
    state.add_task(_queued_task("TASK-0001", created_at=stale_created_at))

    first = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    starvation_first = [alert for alert in first if alert.code == STARVATION]
    assert len(starvation_first) == 1
    assert starvation_first[0].task_id == "TASK-0001"
    assert [alert for alert in second if alert.code == STARVATION] == []


def test_starvation_alert_does_not_fire_before_threshold() -> None:
    state = _new_state()
    service = AlertService(state)
    state.add_task(_queued_task("TASK-0001"))

    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert [alert for alert in alerts if alert.code == STARVATION] == []


def test_robot_waiting_fires_once_idle_past_threshold() -> None:
    # task_interval_seconds=0.0 makes the (task_interval * 2) threshold 0, so
    # any real elapsed time between two check() calls exceeds it.
    state = _new_state()
    service = AlertService(state)
    service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)

    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)

    waiting_alerts = [alert for alert in alerts if alert.code == ROBOT_WAITING]
    assert len(waiting_alerts) == 1
    assert waiting_alerts[0].robot_id == "AMR-01"


def test_robot_waiting_does_not_flood_while_still_idle() -> None:
    state = _new_state()
    service = AlertService(state)
    service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)
    first = service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)

    assert len([alert for alert in first if alert.code == ROBOT_WAITING]) == 1
    assert len([alert for alert in second if alert.code == ROBOT_WAITING]) == 0


def test_robot_waiting_clears_and_can_retrigger_after_leaving_idle() -> None:
    state = _new_state()
    service = AlertService(state)
    service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)
    first = service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)
    assert len([alert for alert in first if alert.code == ROBOT_WAITING]) == 1

    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.status = RobotStatus.MOVING_TO_PICKUP
    state.update_robot(robot)
    service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)

    robot.status = RobotStatus.IDLE
    state.update_robot(robot)
    service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)
    second = service.check(low_battery_threshold=20.0, task_interval_seconds=0.0)

    assert len([alert for alert in second if alert.code == ROBOT_WAITING]) == 1


def test_reset_clears_dedup_state_and_alert_number_sequence() -> None:
    state = _new_state()
    service = AlertService(state)
    _set_battery(state, "AMR-01", 10.0)
    service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    service.reset()
    alerts = service.check(low_battery_threshold=20.0, task_interval_seconds=8.0)

    assert len(alerts) == 1
    assert alerts[0].id == "ALERT-0001"
