import logging
from datetime import UTC, datetime

from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState

logger = logging.getLogger("ev_twin_api")

PICKUP_STATION_ID = "BATTERY_BUFFER"
DROPOFF_STATION_ID = "MARRIAGE_STATION"


class TaskService:
    """Generates battery-delivery tasks into FactoryState.

    Task and payload ids are derived from the current task count, so they
    stay sequential (TASK-0001, TASK-0002, ...) and naturally restart after
    FactoryState.reset() empties the task collection.
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
