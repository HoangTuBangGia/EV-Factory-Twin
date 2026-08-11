import logging
from datetime import UTC, datetime
from typing import cast

from fastapi import Request

from ev_twin_api.core.layout import (
    FACTORY_HEIGHT_M,
    FACTORY_WIDTH_M,
    IDLE_ZONE_X,
    IDLE_ZONE_Y,
    ROBOT_SPAWN_SPACING_M,
    STATIONS,
)
from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.schemas.factory import FactoryLayout, MockFactoryConfig, Station
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.robot import Pose, Robot, RobotStatus, Velocity
from ev_twin_api.schemas.task import Task

logger = logging.getLogger("ev_twin_api")


def _empty_metrics() -> FactoryMetrics:
    return FactoryMetrics(
        completed_tasks=0,
        throughput_per_hour=0.0,
        average_cycle_time_seconds=0.0,
        active_tasks=0,
        queued_tasks=0,
        starvation_events=0,
        fleet_utilization_percent=0.0,
    )


def _initial_robots(robot_count: int) -> dict[str, Robot]:
    now = datetime.now(UTC)
    robots: dict[str, Robot] = {}
    for index in range(robot_count):
        robot_id = f"AMR-{index + 1:02d}"
        robots[robot_id] = Robot(
            id=robot_id,
            name=robot_id,
            status=RobotStatus.IDLE,
            pose=Pose(x=IDLE_ZONE_X + index * ROBOT_SPAWN_SPACING_M, y=IDLE_ZONE_Y, yaw=0.0),
            velocity=Velocity(linear=0.0, angular=0.0),
            battery=100.0,
            last_seen_at=now,
        )
    return robots


class FactoryState:
    """Sole owner of mutable factory runtime state.

    State is in-memory only for this sprint: a backend restart resets
    everything. Durable (PostgreSQL/TimescaleDB) persistence is a later phase.
    """

    def __init__(self, config: MockFactoryConfig) -> None:
        self.config = config
        self.robots: dict[str, Robot] = {}
        self.stations: list[Station] = []
        self.tasks: dict[str, Task] = {}
        self.alerts: list[FactoryAlert] = []
        self.metrics: FactoryMetrics = _empty_metrics()
        self.initialize()

    def initialize(self) -> None:
        self.robots = _initial_robots(self.config.robot_count)
        self.stations = list(STATIONS)
        self.tasks = {}
        self.alerts = []
        self.metrics = _empty_metrics()
        logger.info("factory initialized with %d robots", len(self.robots))

    def reset(self) -> None:
        self.initialize()
        logger.info("factory reset")

    def get_layout(self) -> FactoryLayout:
        return FactoryLayout(
            width_m=FACTORY_WIDTH_M,
            height_m=FACTORY_HEIGHT_M,
            stations=[station.model_copy(deep=True) for station in self.stations],
        )

    def list_robots(self) -> list[Robot]:
        return [robot.model_copy(deep=True) for robot in self.robots.values()]

    def get_robot(self, robot_id: str) -> Robot | None:
        robot = self.robots.get(robot_id)
        return robot.model_copy(deep=True) if robot is not None else None

    def update_robot(self, robot: Robot) -> None:
        self.robots[robot.id] = robot.model_copy(deep=True)

    def list_tasks(self) -> list[Task]:
        return [task.model_copy(deep=True) for task in self.tasks.values()]

    def get_task(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        return task.model_copy(deep=True) if task is not None else None

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task.model_copy(deep=True)

    def list_alerts(self) -> list[FactoryAlert]:
        return [alert.model_copy(deep=True) for alert in self.alerts]

    def add_alert(self, alert: FactoryAlert) -> None:
        self.alerts.append(alert.model_copy(deep=True))

    def get_metrics(self) -> FactoryMetrics:
        return self.metrics.model_copy(deep=True)


def get_factory_state(request: Request) -> FactoryState:
    return cast(FactoryState, request.app.state.factory_state)
