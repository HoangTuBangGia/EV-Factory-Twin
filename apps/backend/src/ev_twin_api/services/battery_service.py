import logging

from ev_twin_api.schemas.robot import Robot, RobotStatus
from ev_twin_api.services.factory_state import FactoryState

logger = logging.getLogger("ev_twin_api")

# Demo parameters only — accelerated for a short, observable demo session, not
# a claim about real battery electrochemistry or discharge curves (guide §9).
MOVING_DRAIN_PERCENT_PER_SECOND = 0.5
PICK_DROP_DRAIN_PERCENT_PER_SECOND = 0.2
IDLE_DRAIN_PERCENT_PER_SECOND = 0.0
CHARGE_RATE_PERCENT_PER_SECOND = 5.0
CHARGE_TARGET_PERCENT = 80.0

_MOVING_STATUSES = frozenset(
    {RobotStatus.MOVING_TO_PICKUP, RobotStatus.DELIVERING, RobotStatus.MOVING_TO_CHARGER}
)
_PICK_DROP_STATUSES = frozenset({RobotStatus.PICKING, RobotStatus.DROPPING})


def apply_battery_tick(status: RobotStatus, battery: float, dt: float) -> float:
    if status in _MOVING_STATUSES:
        delta = -MOVING_DRAIN_PERCENT_PER_SECOND * dt
    elif status in _PICK_DROP_STATUSES:
        delta = -PICK_DROP_DRAIN_PERCENT_PER_SECOND * dt
    elif status == RobotStatus.CHARGING:
        delta = CHARGE_RATE_PERCENT_PER_SECOND * dt
    else:
        delta = -IDLE_DRAIN_PERCENT_PER_SECOND * dt

    return max(0.0, min(100.0, battery + delta))


class BatteryService:
    """Drives the IDLE -> MOVING_TO_CHARGER -> CHARGING -> IDLE charging flow.

    Per-tick drain/charge amounts are computed by `apply_battery_tick` and
    applied by the caller (MockFactory); this class only owns the charging
    state-machine transitions themselves, mirroring TaskService's split
    between domain state mutation and engine orchestration.
    """

    def __init__(self, state: FactoryState) -> None:
        self._state = state

    def start_charging_if_needed(self, robot: Robot, low_battery_threshold: float) -> Robot | None:
        if robot.battery > low_battery_threshold:
            return None
        updated = robot.model_copy(update={"status": RobotStatus.MOVING_TO_CHARGER})
        self._state.update_robot(updated)
        logger.info(
            "low battery condition entered: %s battery=%.1f%%, heading to charger",
            robot.id,
            robot.battery,
        )
        return updated

    def arrive_at_charger(self, robot_id: str) -> Robot | None:
        robot = self._state.get_robot(robot_id)
        if robot is None:
            return None
        updated = robot.model_copy(update={"status": RobotStatus.CHARGING})
        self._state.update_robot(updated)
        logger.info("%s started charging", robot_id)
        return updated

    def finish_charging_if_ready(self, robot_id: str) -> Robot | None:
        robot = self._state.get_robot(robot_id)
        if robot is None or robot.battery < CHARGE_TARGET_PERCENT:
            return None
        updated = robot.model_copy(update={"status": RobotStatus.IDLE})
        self._state.update_robot(updated)
        return updated
