import logging
from datetime import UTC, datetime

from ev_twin_api.schemas.alert import AlertSeverity, FactoryAlert
from ev_twin_api.schemas.robot import Robot, RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.metrics_service import STARVATION_THRESHOLD_SECONDS

logger = logging.getLogger("ev_twin_api")

LOW_BATTERY = "LOW_BATTERY"
ROBOT_WAITING = "ROBOT_WAITING"
TASK_BACKLOG = "TASK_BACKLOG"
STARVATION = "STARVATION"
ROBOT_ERROR = "ROBOT_ERROR"

SEVERITY_BY_CODE = {
    LOW_BATTERY: AlertSeverity.WARNING,
    ROBOT_WAITING: AlertSeverity.INFO,
    TASK_BACKLOG: AlertSeverity.WARNING,
    STARVATION: AlertSeverity.WARNING,
    ROBOT_ERROR: AlertSeverity.CRITICAL,
}

# A robot sitting IDLE longer than this multiple of task_interval_seconds is
# unusually long without picking up work — a demo heuristic, not a claim
# about real fleet scheduling targets.
ROBOT_WAITING_THRESHOLD_MULTIPLIER = 2.0


class AlertService:
    """Generates deduplicated FactoryAlerts from the current FactoryState.

    Stateful alerts (tied to a condition that persists across ticks, e.g. a
    robot staying low on battery) are deduplicated by a private key such as
    "LOW_BATTERY:AMR-01": the alert fires once on entering the condition,
    stays suppressed while it holds, and can fire again only after the
    condition clears and later re-triggers.
    """

    def __init__(self, state: FactoryState) -> None:
        self._state = state
        self._next_alert_number = 1
        self._active_condition_keys: set[str] = set()
        self._idle_since: dict[str, datetime] = {}

    def reset(self) -> None:
        self._next_alert_number = 1
        self._active_condition_keys.clear()
        self._idle_since.clear()

    def check(
        self, *, low_battery_threshold: float, task_interval_seconds: float
    ) -> list[FactoryAlert]:
        robots = self._state.list_robots()
        tasks = self._state.list_tasks()

        new_alerts: list[FactoryAlert] = [
            *self._check_low_battery(robots, low_battery_threshold),
            *self._check_robot_waiting(robots, task_interval_seconds),
            *self._check_robot_error(robots),
            *self._check_task_backlog(tasks),
            *self._check_starvation(tasks),
        ]

        for alert in new_alerts:
            self._state.add_alert(alert)
        return new_alerts

    def _create_alert(
        self,
        code: str,
        message: str,
        *,
        robot_id: str | None = None,
        task_id: str | None = None,
    ) -> FactoryAlert:
        alert = FactoryAlert(
            id=f"ALERT-{self._next_alert_number:04d}",
            severity=SEVERITY_BY_CODE[code],
            code=code,
            message=message,
            robot_id=robot_id,
            task_id=task_id,
            timestamp=datetime.now(UTC),
        )
        self._next_alert_number += 1
        logger.info("alert created: %s (%s)", alert.id, alert.code)
        return alert

    def _check_low_battery(
        self, robots: list[Robot], low_battery_threshold: float
    ) -> list[FactoryAlert]:
        alerts: list[FactoryAlert] = []
        for robot in robots:
            key = f"{LOW_BATTERY}:{robot.id}"
            if robot.battery <= low_battery_threshold:
                if key not in self._active_condition_keys:
                    self._active_condition_keys.add(key)
                    alerts.append(
                        self._create_alert(
                            LOW_BATTERY,
                            f"{robot.id} battery low ({robot.battery:.1f}%)",
                            robot_id=robot.id,
                        )
                    )
            else:
                self._active_condition_keys.discard(key)
        return alerts

    def _check_robot_waiting(
        self, robots: list[Robot], task_interval_seconds: float
    ) -> list[FactoryAlert]:
        threshold = task_interval_seconds * ROBOT_WAITING_THRESHOLD_MULTIPLIER
        now = datetime.now(UTC)
        alerts: list[FactoryAlert] = []
        still_idle_ids: set[str] = set()

        for robot in robots:
            if robot.status != RobotStatus.IDLE:
                continue
            still_idle_ids.add(robot.id)
            idle_since = self._idle_since.setdefault(robot.id, now)
            idle_seconds = (now - idle_since).total_seconds()
            key = f"{ROBOT_WAITING}:{robot.id}"
            if idle_seconds > threshold and key not in self._active_condition_keys:
                self._active_condition_keys.add(key)
                alerts.append(
                    self._create_alert(
                        ROBOT_WAITING,
                        f"{robot.id} idle for {idle_seconds:.0f}s without a new task",
                        robot_id=robot.id,
                    )
                )

        for robot_id in list(self._idle_since):
            if robot_id not in still_idle_ids:
                del self._idle_since[robot_id]
                self._active_condition_keys.discard(f"{ROBOT_WAITING}:{robot_id}")

        return alerts

    def _check_robot_error(self, robots: list[Robot]) -> list[FactoryAlert]:
        alerts: list[FactoryAlert] = []
        for robot in robots:
            key = f"{ROBOT_ERROR}:{robot.id}"
            if robot.status == RobotStatus.ERROR:
                if key not in self._active_condition_keys:
                    self._active_condition_keys.add(key)
                    alerts.append(
                        self._create_alert(
                            ROBOT_ERROR, f"{robot.id} entered ERROR state", robot_id=robot.id
                        )
                    )
            else:
                self._active_condition_keys.discard(key)
        return alerts

    def _check_task_backlog(self, tasks: list[Task]) -> list[FactoryAlert]:
        queued_count = sum(1 for task in tasks if task.status == TaskStatus.QUEUED)
        robot_count = len(self._state.robots)

        if queued_count > robot_count:
            if TASK_BACKLOG not in self._active_condition_keys:
                self._active_condition_keys.add(TASK_BACKLOG)
                return [
                    self._create_alert(
                        TASK_BACKLOG,
                        f"{queued_count} tasks queued, exceeding fleet size ({robot_count})",
                    )
                ]
        else:
            self._active_condition_keys.discard(TASK_BACKLOG)
        return []

    def _check_starvation(self, tasks: list[Task]) -> list[FactoryAlert]:
        now = datetime.now(UTC)
        alerts: list[FactoryAlert] = []
        for task in tasks:
            if task.status != TaskStatus.QUEUED:
                continue
            key = f"{STARVATION}:{task.task_id}"
            if key in self._active_condition_keys:
                continue
            waited_seconds = (now - task.created_at).total_seconds()
            if waited_seconds > STARVATION_THRESHOLD_SECONDS:
                self._active_condition_keys.add(key)
                alerts.append(
                    self._create_alert(
                        STARVATION,
                        f"{task.task_id} has been queued for {waited_seconds:.0f}s",
                        task_id=task.task_id,
                    )
                )
        return alerts
