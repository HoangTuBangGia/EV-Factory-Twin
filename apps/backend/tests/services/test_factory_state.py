from uuid import uuid4

from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.services.factory_state import FactoryState
from twin_core.default_layout import default_layout_content

LAYOUT = default_layout_content()


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
        assert 0 <= robot.pose.x <= LAYOUT.width
        assert 0 <= robot.pose.y <= LAYOUT.height


def test_robot_poses_do_not_overlap() -> None:
    state = _new_state()
    positions = [(robot.pose.x, robot.pose.y) for robot in state.robots.values()]
    assert len(positions) == len(set(positions))


def test_layout_uses_canonical_plant_coordinates() -> None:
    state = _new_state()
    layout = state.get_layout()
    assert layout.width_m == 120
    assert layout.height_m == 40

    expected = {
        "BATTERY_BUFFER": (32, 29),
        "MARRIAGE_STATION": (52, 6),
        "CHARGING_STATION": (32, 11),
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


def test_applied_layout_controls_runtime_route_and_station_geometry() -> None:
    state = _new_state(robot_count=2)
    moved = LAYOUT.model_copy(
        update={
            "stations": [
                station.model_copy(update={"x": 35.0})
                if station.id == "CHARGING_STATION"
                else station
                for station in LAYOUT.stations
            ]
        }
    )

    state.apply_layout(moved, "BATTERY_DELIVERY")
    state.reset()

    assert next(station for station in state.stations if station.id == "CHARGING_STATION").x == 35
    assert state.route_waypoints(("BATTERY_BUFFER", "MARRIAGE_STATION")) == tuple(
        (point.x, point.y) for point in moved.routes[0].waypoints
    )


def test_edge_state_starts_empty_and_registry_preserves_known_telemetry() -> None:
    state = FactoryState(MockFactoryConfig(), seed_mock_robots=False)
    assert state.list_robots() == []

    assert state.synchronize_robot_registry(["EDGE-01", "EDGE-02"])
    edge_01 = state.get_robot("EDGE-01")
    assert edge_01 is not None
    assert edge_01.status == RobotStatus.OFFLINE
    edge_01.battery = 73.0
    state.update_robot(edge_01)

    assert state.synchronize_robot_registry(["EDGE-01", "EDGE-03"])
    assert state.get_robot("EDGE-01").battery == 73.0
    assert state.get_robot("EDGE-02") is None
    assert state.get_robot("EDGE-03") is not None
    assert not state.synchronize_robot_registry(["EDGE-01", "EDGE-03"])


def test_bridge_registry_does_not_replace_mock_robots() -> None:
    state = _new_state(robot_count=2)

    assert not state.synchronize_robot_registry(["EDGE-01"])
    assert {robot.id for robot in state.list_robots()} == {"AMR-01", "AMR-02"}


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
            id=uuid4(),
            dedupe_key="LOW_BATTERY:AMR-01",
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
