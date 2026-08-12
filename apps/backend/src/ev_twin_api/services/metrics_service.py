from datetime import UTC, datetime

from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState

PRODUCTIVE_STATUSES = frozenset(
    {
        RobotStatus.MOVING_TO_PICKUP,
        RobotStatus.PICKING,
        RobotStatus.DELIVERING,
        RobotStatus.DROPPING,
    }
)

# Wall-clock seconds: Task.created_at is a real timestamp, not a simulated
# one, so "how long has this task been queued" is inherently a wall-clock
# question — unlike throughput_per_hour, which is measured against simulated
# elapsed time. Not a physical/industry claim, just a demo threshold.
STARVATION_THRESHOLD_SECONDS = 30.0


class MetricsService:
    """Recomputes FactoryMetrics from the current FactoryState each call.

    starvation_events is the exception: it's a cumulative counter, not a
    fresh recount, so each starved task is only counted once (tracked in
    `_starved_task_ids`) rather than incrementing again on every tick it
    stays queued past the threshold.
    """

    def __init__(self, state: FactoryState) -> None:
        self._state = state
        self._starvation_event_count = 0
        self._starved_task_ids: set[str] = set()

    def reset(self) -> None:
        self._starvation_event_count = 0
        self._starved_task_ids.clear()

    def recalculate(self, simulated_elapsed_seconds: float) -> FactoryMetrics:
        tasks = self._state.list_tasks()
        robots = self._state.list_robots()

        completed = [task for task in tasks if task.status == TaskStatus.COMPLETED]
        queued = [task for task in tasks if task.status == TaskStatus.QUEUED]
        active = [
            task
            for task in tasks
            if task.status not in (TaskStatus.QUEUED, TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]

        throughput_per_hour = 0.0
        if simulated_elapsed_seconds > 0:
            elapsed_hours = simulated_elapsed_seconds / 3600.0
            throughput_per_hour = len(completed) / elapsed_hours

        cycle_times = [
            (task.completed_at - task.created_at).total_seconds()
            for task in completed
            if task.completed_at is not None
        ]
        average_cycle_time_seconds = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0

        online_robots = [robot for robot in robots if robot.status != RobotStatus.OFFLINE]
        productive_robots = [
            robot for robot in online_robots if robot.status in PRODUCTIVE_STATUSES
        ]
        fleet_utilization_percent = (
            len(productive_robots) / len(online_robots) * 100.0 if online_robots else 0.0
        )

        self._record_starvation(queued)

        return FactoryMetrics(
            completed_tasks=len(completed),
            throughput_per_hour=throughput_per_hour,
            average_cycle_time_seconds=average_cycle_time_seconds,
            active_tasks=len(active),
            queued_tasks=len(queued),
            starvation_events=self._starvation_event_count,
            fleet_utilization_percent=fleet_utilization_percent,
        )

    def _record_starvation(self, queued_tasks: list[Task]) -> None:
        now = datetime.now(UTC)
        for task in queued_tasks:
            if task.task_id in self._starved_task_ids:
                continue
            waited_seconds = (now - task.created_at).total_seconds()
            if waited_seconds > STARVATION_THRESHOLD_SECONDS:
                self._starvation_event_count += 1
                self._starved_task_ids.add(task.task_id)
