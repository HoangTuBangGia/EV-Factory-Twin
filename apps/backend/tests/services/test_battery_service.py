from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.services.battery_service import (
    CHARGE_TARGET_PERCENT,
    BatteryService,
    apply_battery_tick,
)
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.task_service import TaskService


def _new_state(robot_count: int = 1) -> FactoryState:
    return FactoryState(config=MockFactoryConfig(robot_count=robot_count))


def test_moving_drains_battery() -> None:
    battery = apply_battery_tick(RobotStatus.MOVING_TO_PICKUP, 50.0, 10.0)
    assert battery == 45.0


def test_delivering_and_moving_to_charger_use_the_same_moving_rate() -> None:
    delivering = apply_battery_tick(RobotStatus.DELIVERING, 50.0, 10.0)
    to_charger = apply_battery_tick(RobotStatus.MOVING_TO_CHARGER, 50.0, 10.0)
    assert delivering == to_charger == 45.0


def test_picking_and_dropping_drain_less_than_moving() -> None:
    picking = apply_battery_tick(RobotStatus.PICKING, 50.0, 10.0)
    dropping = apply_battery_tick(RobotStatus.DROPPING, 50.0, 10.0)
    moving = apply_battery_tick(RobotStatus.MOVING_TO_PICKUP, 50.0, 10.0)
    assert picking == dropping == 48.0
    assert picking > moving


def test_idle_drain_is_negligible() -> None:
    assert apply_battery_tick(RobotStatus.IDLE, 50.0, 100.0) == 50.0


def test_charging_increases_battery() -> None:
    assert apply_battery_tick(RobotStatus.CHARGING, 50.0, 2.0) == 60.0


def test_battery_never_goes_below_zero() -> None:
    assert apply_battery_tick(RobotStatus.MOVING_TO_PICKUP, 1.0, 100.0) == 0.0


def test_battery_never_exceeds_one_hundred() -> None:
    assert apply_battery_tick(RobotStatus.CHARGING, 99.0, 100.0) == 100.0


def test_start_charging_if_needed_triggers_at_or_below_threshold() -> None:
    state = _new_state()
    service = BatteryService(state)
    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 20.0
    state.update_robot(robot)

    updated = service.start_charging_if_needed(robot, low_battery_threshold=20.0)

    assert updated is not None
    assert updated.status == RobotStatus.MOVING_TO_CHARGER
    stored = state.get_robot("AMR-01")
    assert stored is not None
    assert stored.status == RobotStatus.MOVING_TO_CHARGER


def test_start_charging_if_needed_does_nothing_above_threshold() -> None:
    state = _new_state()
    service = BatteryService(state)
    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 21.0
    state.update_robot(robot)

    assert service.start_charging_if_needed(robot, low_battery_threshold=20.0) is None
    stored = state.get_robot("AMR-01")
    assert stored is not None
    assert stored.status == RobotStatus.IDLE


def test_low_battery_robot_is_excluded_from_new_task_assignment() -> None:
    state = _new_state()
    task_service = TaskService(state)
    task_service.generate_task()

    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 20.0
    state.update_robot(robot)

    assert task_service.select_assignment(low_battery_threshold=20.0) is None


def test_charging_state_machine_progresses_to_idle_at_target() -> None:
    state = _new_state()
    battery_service = BatteryService(state)
    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = 15.0
    state.update_robot(robot)

    triggered = battery_service.start_charging_if_needed(robot, low_battery_threshold=20.0)
    assert triggered is not None
    assert triggered.status == RobotStatus.MOVING_TO_CHARGER

    charging = battery_service.arrive_at_charger("AMR-01")
    assert charging is not None
    assert charging.status == RobotStatus.CHARGING

    assert battery_service.finish_charging_if_ready("AMR-01") is None

    robot = state.get_robot("AMR-01")
    assert robot is not None
    robot.battery = CHARGE_TARGET_PERCENT
    state.update_robot(robot)

    finished = battery_service.finish_charging_if_ready("AMR-01")
    assert finished is not None
    assert finished.status == RobotStatus.IDLE
