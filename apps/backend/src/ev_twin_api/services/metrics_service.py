import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.schemas.websocket import metrics_updated_event
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.websocket_manager import WebSocketManager

logger = logging.getLogger("ev_twin_api")

PRODUCTIVE_STATUSES = frozenset(
    {
        RobotStatus.MOVING_TO_PICKUP,
        RobotStatus.PICKING,
        RobotStatus.DELIVERING,
        RobotStatus.DROPPING,
    }
)

# Wall-clock seconds since this backend first observed a task queued. Source
# timestamps may be ROS/Gazebo simulation time and are not comparable to UTC now.
STARVATION_THRESHOLD_SECONDS = 30.0


class MetricsService:
    """Recomputes FactoryMetrics from the current FactoryState each call.

    starvation_events is the exception: it's a cumulative counter, not a
    fresh recount, so each starved task is only counted once (tracked in
    `_starved_task_ids`) rather than incrementing again on every tick it
    stays queued past the threshold.
    """

    def __init__(
        self,
        state: FactoryState,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._state = state
        self._clock = clock or (lambda: datetime.now(UTC))
        self._starvation_event_count = 0
        self._starved_task_ids: set[str] = set()
        self._queued_since: dict[str, datetime] = {}

    def reset(self) -> None:
        self._starvation_event_count = 0
        self._starved_task_ids.clear()
        self._queued_since.clear()

    def recalculate(self, simulated_elapsed_seconds: float) -> FactoryMetrics:
        tasks = self._state.list_tasks()
        robots = self._state.list_robots()

        completed = [task for task in tasks if task.status == TaskStatus.COMPLETED]
        queued = [task for task in tasks if task.status == TaskStatus.QUEUED]
        active = [
            task
            for task in tasks
            if task.status
            not in (
                TaskStatus.QUEUED,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.TIMED_OUT,
            )
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
        now = self._clock()
        queued_ids = {task.task_id for task in queued_tasks}
        for task_id in self._queued_since.keys() - queued_ids:
            del self._queued_since[task_id]
        for task in queued_tasks:
            if task.task_id in self._starved_task_ids:
                continue
            queued_since = self._queued_since.setdefault(task.task_id, now)
            waited_seconds = (now - queued_since).total_seconds()
            if waited_seconds > STARVATION_THRESHOLD_SECONDS:
                self._starvation_event_count += 1
                self._starved_task_ids.add(task.task_id)


class RuntimeMetricsPublisher:
    """Own live-source KPI refresh without duplicating the mock engine loop."""

    def __init__(
        self,
        state: FactoryState,
        websockets: WebSocketManager,
        *,
        enabled: bool,
        interval_seconds: float = 1.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("runtime metrics interval must be positive")
        self._state = state
        self._websockets = websockets
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._monotonic = monotonic
        self._metrics = MetricsService(state)
        self._started_at = monotonic()
        self._last_publish_at: float | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, self._monotonic() - self._started_at)

    async def start(self) -> None:
        if not self._enabled or self._task is not None:
            return
        self._started_at = self._monotonic()
        self._task = asyncio.create_task(self._run(), name="runtime-metrics-publisher")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def refresh(self, *, force: bool = False) -> bool:
        if not self._enabled:
            return False
        async with self._lock:
            now = self._monotonic()
            if (
                not force
                and self._last_publish_at is not None
                and now - self._last_publish_at < self._interval_seconds
            ):
                return False
            metrics = self._metrics.recalculate(self.elapsed_seconds)
            self._state.update_metrics(metrics)
            await self._websockets.broadcast(metrics_updated_event(metrics))
            self._last_publish_at = now
            return True

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            try:
                await self.refresh(force=True)
            except Exception:
                logger.exception("runtime metrics refresh failed; retrying next cadence")
