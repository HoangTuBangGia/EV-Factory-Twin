import logging
import math
from datetime import UTC, datetime

from ev_twin_api.schemas.robot import Robot, RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState

logger = logging.getLogger("ev_twin_api")

PICKUP_STATION_ID = "BATTERY_BUFFER"
DROPOFF_STATION_ID = "MARRIAGE_STATION"


class TaskService:
    """Generates and drives battery-delivery tasks against FactoryState.

    Task and payload ids are derived from the current task count, so they
    stay sequential (TASK-0001, TASK-0002, ...) and naturally restart after
    FactoryState.reset() empties the task collection.

    Task status and robot status advance in lockstep:
    QUEUED/IDLE -> ASSIGNED/MOVING_TO_PICKUP -> PICKUP/PICKING ->
    IN_PROGRESS/DELIVERING -> DELIVERED/DROPPING -> COMPLETED/IDLE.
    Movement (and therefore the MOVING_TO_PICKUP/DELIVERING arrival
    triggers) is driven by MockFactory; this service only owns the domain
    state transitions themselves.
    """

    def __init__(self, state: FactoryState) -> None:
        self._state = state

    def generate_task(self) -> Task:
        sequence_number = len(self._state.tasks) + 1
        task = Task(
            task_id=f"TASK-{sequence_number:04d}",
            payload_id=f"BP-{sequence_number:04d}",
            pickup=PICKUP_STATION_ID,
            dropoff=DROPOFF_STATION_ID,
            status=TaskStatus.QUEUED,
            created_at=datetime.now(UTC),
        )
        self._state.add_task(task)
        logger.info("task created: %s", task.task_id)
        return task

    def select_assignment(self, low_battery_threshold: float) -> tuple[Robot, Task] | None:
        """Pick the nearest eligible IDLE robot for the oldest QUEUED task (guide §8)."""
        queued_tasks = sorted(
            (task for task in self._state.list_tasks() if task.status == TaskStatus.QUEUED),
            key=lambda task: task.created_at,
        )
        if not queued_tasks:
            return None

        candidates = [
            robot
            for robot in self._state.list_robots()
            if robot.status == RobotStatus.IDLE and robot.battery > low_battery_threshold
        ]
        if not candidates:
            return None

        pickup_station = next(
            station for station in self._state.stations if station.id == PICKUP_STATION_ID
        )
        selected_robot = min(
            candidates,
            key=lambda robot: math.hypot(
                robot.pose.x - pickup_station.x, robot.pose.y - pickup_station.y
            ),
        )
        return selected_robot, queued_tasks[0]

    def assign(self, robot: Robot, task: Task) -> Task:
        now = datetime.now(UTC)
        updated_task = task.model_copy(
            update={
                "status": TaskStatus.ASSIGNED,
                "assigned_robot_id": robot.id,
                "started_at": now,
            }
        )
        self._state.update_task(updated_task)
        self._state.update_robot(
            robot.model_copy(
                update={"status": RobotStatus.MOVING_TO_PICKUP, "task_id": task.task_id}
            )
        )
        logger.info("task assigned: %s -> %s", task.task_id, robot.id)
        return updated_task

    def arrive_at_pickup(self, robot_id: str) -> Task:
        robot, task = self._robot_and_task(robot_id)
        self._state.update_robot(robot.model_copy(update={"status": RobotStatus.PICKING}))
        updated_task = task.model_copy(update={"status": TaskStatus.PICKUP})
        self._state.update_task(updated_task)
        return updated_task

    def finish_pickup(self, robot_id: str) -> Task:
        robot, task = self._robot_and_task(robot_id)
        self._state.update_robot(
            robot.model_copy(
                update={"status": RobotStatus.DELIVERING, "payload_id": task.payload_id}
            )
        )
        updated_task = task.model_copy(update={"status": TaskStatus.IN_PROGRESS})
        self._state.update_task(updated_task)
        return updated_task

    def arrive_at_dropoff(self, robot_id: str) -> Task:
        robot, task = self._robot_and_task(robot_id)
        self._state.update_robot(robot.model_copy(update={"status": RobotStatus.DROPPING}))
        updated_task = task.model_copy(update={"status": TaskStatus.DELIVERED})
        self._state.update_task(updated_task)
        return updated_task

    def finish_dropoff(self, robot_id: str) -> Task:
        robot, task = self._robot_and_task(robot_id)
        now = datetime.now(UTC)
        self._state.update_robot(
            robot.model_copy(
                update={"status": RobotStatus.IDLE, "task_id": None, "payload_id": None}
            )
        )
        updated_task = task.model_copy(update={"status": TaskStatus.COMPLETED, "completed_at": now})
        self._state.update_task(updated_task)
        logger.info("task completed: %s", task.task_id)
        return updated_task

    def _robot_and_task(self, robot_id: str) -> tuple[Robot, Task]:
        robot = self._state.get_robot(robot_id)
        if robot is None or robot.task_id is None:
            raise ValueError(f"Robot '{robot_id}' has no active task")
        task = self._state.get_task(robot.task_id)
        if task is None:
            raise ValueError(f"Task '{robot.task_id}' not found for robot '{robot_id}'")
        return robot, task
