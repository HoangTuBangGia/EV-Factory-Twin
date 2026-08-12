from ev_twin_api.core.layout import FACTORY_HEIGHT_M, FACTORY_WIDTH_M
from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState


def _new_state(**config_overrides: object) -> FactoryState:
    return FactoryState(config=MockFactoryConfig(**config_overrides))  # type: ignore[arg-type]


def _robots_excluding_timestamps(state: FactoryState) -> dict[str, dict[str, object]]:
    return {
        robot_id: robot.model_dump(exclude={"last_seen_at"})
        for robot_id, robot in state.robots.items()
    }


def test_initialize_creates_five_robots_by_default() -> None:
    state = _new_state()
    assert set(state.robots.keys()) == {f"AMR-{i:02d}" for i in range(1, 6)}


def test_robots_start_idle_full_battery_no_task() -> None:
    state = _new_state()
    for robot in state.robots.values():
        assert robot.status == RobotStatus.IDLE
        assert robot.battery == 100.0
        assert robot.task_id is None
        assert robot.payload_id is None


def test_robot_poses_within_factory_bounds() -> None:
    state = _new_state()
    for robot in state.robots.values():
        assert 0 <= robot.pose.x <= FACTORY_WIDTH_M
        assert 0 <= robot.pose.y <= FACTORY_HEIGHT_M


def test_robot_poses_do_not_overlap() -> None:
    state = _new_state()
    positions = [(robot.pose.x, robot.pose.y) for robot in state.robots.values()]
    assert len(positions) == len(set(positions))


def test_layout_has_six_stations_with_expected_coordinates() -> None:
    state = _new_state()
    layout = state.get_layout()
    assert layout.width_m == FACTORY_WIDTH_M
    assert layout.height_m == FACTORY_HEIGHT_M

    expected = {
        "BATTERY_BUFFER": (2, 4),
        "INTERSECTION_A": (8, 4),
        "INTERSECTION_B": (12, 8),
        "MARRIAGE_STATION": (16, 8),
        "CHARGING_STATION": (2, 12),
        "IDLE_ZONE": (5, 12),
    }
    assert {station.id: (station.x, station.y) for station in layout.stations} == expected


def test_initialize_is_deterministic() -> None:
    state_a = _new_state()
    state_b = _new_state()
    assert _robots_excluding_timestamps(state_a) == _robots_excluding_timestamps(state_b)
    assert state_a.get_layout() == state_b.get_layout()


def test_robot_count_from_config() -> None:
    state = _new_state(robot_count=3)
    assert set(state.robots.keys()) == {"AMR-01", "AMR-02", "AMR-03"}


def test_get_unknown_robot_returns_none() -> None:
    state = _new_state()
    assert state.get_robot("AMR-99") is None


def test_get_unknown_task_returns_none() -> None:
    state = _new_state()
    assert state.get_task("TASK-99") is None


def test_reset_restores_initial_state() -> None:
    state = _new_state()
    initial_robots = _robots_excluding_timestamps(state)

    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.status = RobotStatus.CHARGING
    robot.battery = 10.0
    state.update_robot(robot)

    state.add_task(
        Task(
            task_id="TASK-0001",
            payload_id="BP-0001",
            pickup="BATTERY_BUFFER",
            dropoff="MARRIAGE_STATION",
            status=TaskStatus.QUEUED,
            created_at=robot.last_seen_at,
        )
    )
    state.add_alert(
        FactoryAlert(
            id="ALERT-0001",
            severity=AlertSeverity.WARNING,
            code=AlertCode.LOW_BATTERY,
            message="low battery",
            timestamp=robot.last_seen_at,
        )
    )

    state.reset()

    assert _robots_excluding_timestamps(state) == initial_robots
    assert state.tasks == {}
    assert state.alerts == []


def test_snapshots_are_copies_not_shared_references() -> None:
    state = _new_state()

    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 0.0
    robot.pose.x = 999.0

    stored = state.get_robot("AMR-01")
    assert stored is not None
    assert stored.battery == 100.0
    assert stored.pose.x != 999.0

    robots = state.list_robots()
    robots.clear()
    assert len(state.robots) == 5
