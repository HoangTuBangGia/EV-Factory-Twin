from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.task_service import TaskService


def _new_service(robot_count: int = 5) -> tuple[TaskService, FactoryState]:
    state = FactoryState(config=MockFactoryConfig(robot_count=robot_count))
    return TaskService(state), state


def _place_robot(state: FactoryState, robot_id: str, *, x: float, y: float, battery: float) -> None:
    robot = state.get_robot(robot_id)
    assert robot is not None
    robot.pose.x = x
    robot.pose.y = y
    robot.battery = battery
    state.update_robot(robot)


def _generate_and_assign(
    service: TaskService, state: FactoryState, robot_id: str = "AMR-01"
) -> Task:
    task = service.generate_task()
    robot = state.get_robot(robot_id)
    assert robot is not None
    service.assign(robot, task)
    return task


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


def test_select_assignment_picks_nearest_eligible_robot() -> None:
    # exact scenario from the guide: BATTERY_BUFFER is at (2, 4), so an offset
    # along +x gives a simple, exact Euclidean distance from it.
    service, state = _new_service(robot_count=3)
    _place_robot(state, "AMR-01", x=7.0, y=4.0, battery=80.0)  # distance 5m
    _place_robot(state, "AMR-02", x=4.0, y=4.0, battery=10.0)  # distance 2m, but low battery
    _place_robot(state, "AMR-03", x=6.0, y=4.0, battery=70.0)  # distance 4m
    task = service.generate_task()

    result = service.select_assignment(low_battery_threshold=20.0)

    assert result is not None
    selected_robot, selected_task = result
    assert selected_robot.id == "AMR-03"
    assert selected_task.task_id == task.task_id


def test_select_assignment_excludes_battery_at_or_below_threshold() -> None:
    service, state = _new_service(robot_count=1)
    service.generate_task()

    _place_robot(state, "AMR-01", x=5.0, y=12.0, battery=20.0)
    assert service.select_assignment(low_battery_threshold=20.0) is None

    _place_robot(state, "AMR-01", x=5.0, y=12.0, battery=20.01)
    result = service.select_assignment(low_battery_threshold=20.0)
    assert result is not None
    assert result[0].id == "AMR-01"


def test_select_assignment_returns_none_without_queued_tasks() -> None:
    service, _state = _new_service(robot_count=1)
    assert service.select_assignment(low_battery_threshold=20.0) is None


def test_select_assignment_returns_none_without_eligible_robot() -> None:
    service, state = _new_service(robot_count=1)
    service.generate_task()
    _place_robot(state, "AMR-01", x=5.0, y=12.0, battery=5.0)

    assert service.select_assignment(low_battery_threshold=20.0) is None

    # task stays QUEUED, ready for the scheduler to retry later
    task = state.list_tasks()[0]
    assert task.status == TaskStatus.QUEUED


def test_queued_task_becomes_assignable_once_a_robot_recovers() -> None:
    service, state = _new_service(robot_count=1)
    task = service.generate_task()
    _place_robot(state, "AMR-01", x=5.0, y=12.0, battery=5.0)
    assert service.select_assignment(low_battery_threshold=20.0) is None

    _place_robot(state, "AMR-01", x=5.0, y=12.0, battery=100.0)
    result = service.select_assignment(low_battery_threshold=20.0)

    assert result is not None
    assert result[0].id == "AMR-01"
    assert result[1].task_id == task.task_id


def test_assign_updates_task_and_robot() -> None:
    service, state = _new_service(robot_count=1)
    task = service.generate_task()
    robot = state.get_robot("AMR-01")
    assert robot is not None

    service.assign(robot, task)

    updated_robot = state.get_robot("AMR-01")
    updated_task = state.get_task(task.task_id)
    assert updated_robot is not None
    assert updated_task is not None
    assert updated_robot.status == RobotStatus.MOVING_TO_PICKUP
    assert updated_robot.task_id == task.task_id
    assert updated_task.status == TaskStatus.ASSIGNED
    assert updated_task.assigned_robot_id == "AMR-01"
    assert updated_task.started_at is not None


def test_arrive_at_pickup_transitions_to_picking() -> None:
    service, state = _new_service(robot_count=1)
    task = _generate_and_assign(service, state)

    service.arrive_at_pickup("AMR-01")

    updated_robot = state.get_robot("AMR-01")
    updated_task = state.get_task(task.task_id)
    assert updated_robot is not None
    assert updated_task is not None
    assert updated_robot.status == RobotStatus.PICKING
    assert updated_task.status == TaskStatus.PICKUP


def test_finish_pickup_attaches_payload_and_starts_delivering() -> None:
    service, state = _new_service(robot_count=1)
    task = _generate_and_assign(service, state)
    service.arrive_at_pickup("AMR-01")

    service.finish_pickup("AMR-01")

    updated_robot = state.get_robot("AMR-01")
    updated_task = state.get_task(task.task_id)
    assert updated_robot is not None
    assert updated_task is not None
    assert updated_robot.status == RobotStatus.DELIVERING
    assert updated_robot.payload_id == task.payload_id
    assert updated_task.status == TaskStatus.DELIVERING


def test_arrive_at_dropoff_transitions_to_dropping() -> None:
    service, state = _new_service(robot_count=1)
    task = _generate_and_assign(service, state)
    service.arrive_at_pickup("AMR-01")
    service.finish_pickup("AMR-01")

    service.arrive_at_dropoff("AMR-01")

    updated_robot = state.get_robot("AMR-01")
    updated_task = state.get_task(task.task_id)
    assert updated_robot is not None
    assert updated_task is not None
    assert updated_robot.status == RobotStatus.DROPPING
    assert updated_task.status == TaskStatus.DELIVERING


def test_finish_dropoff_completes_task_and_frees_robot() -> None:
    service, state = _new_service(robot_count=1)
    task = _generate_and_assign(service, state)
    service.arrive_at_pickup("AMR-01")
    service.finish_pickup("AMR-01")
    service.arrive_at_dropoff("AMR-01")

    service.finish_dropoff("AMR-01")

    updated_robot = state.get_robot("AMR-01")
    updated_task = state.get_task(task.task_id)
    assert updated_robot is not None
    assert updated_task is not None
    assert updated_robot.status == RobotStatus.IDLE
    assert updated_robot.task_id is None
    assert updated_robot.payload_id is None
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.completed_at is not None
