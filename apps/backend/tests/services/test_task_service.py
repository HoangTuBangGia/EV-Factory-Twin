from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.task import TaskStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.task_service import TaskService


def _new_service() -> tuple[TaskService, FactoryState]:
    state = FactoryState(config=MockFactoryConfig())
    return TaskService(state), state


def test_generated_task_is_queued() -> None:
    service, _state = _new_service()
    task = service.generate_task()
    assert task.status == TaskStatus.QUEUED


def test_generated_task_has_expected_content() -> None:
    service, _state = _new_service()
    task = service.generate_task()

    assert task.type == "DELIVER_BATTERY"
    assert task.pickup == "BATTERY_BUFFER"
    assert task.dropoff == "MARRIAGE_STATION"
    assert task.assigned_robot_id is None
    assert task.started_at is None
    assert task.completed_at is None
    assert task.created_at is not None


def test_task_and_payload_ids_are_sequential_without_gaps_or_duplicates() -> None:
    service, _state = _new_service()
    tasks = [service.generate_task() for _ in range(3)]

    assert [task.task_id for task in tasks] == ["TASK-0001", "TASK-0002", "TASK-0003"]
    assert [task.payload_id for task in tasks] == ["BP-0001", "BP-0002", "BP-0003"]


def test_generated_task_is_stored_in_factory_state() -> None:
    service, state = _new_service()
    task = service.generate_task()

    stored = state.get_task(task.task_id)
    assert stored is not None
    assert stored.task_id == task.task_id


def test_task_sequence_restarts_after_state_reset() -> None:
    service, state = _new_service()
    service.generate_task()
    service.generate_task()

    state.reset()
    task = service.generate_task()

    assert task.task_id == "TASK-0001"
    assert task.payload_id == "BP-0001"
