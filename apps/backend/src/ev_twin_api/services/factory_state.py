import logging
import math
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import Depends, Request
from twin_core.default_layout import DEFAULT_ROUTE_ID, default_layout_content
from twin_core.models.layout import LayoutRoute, LayoutVersionContent, RouteKind, StationType
from twin_core.routing import shortest_station_path

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


STATION_RUNTIME_TYPES = {
    StationType.BATTERY_BUFFER: "BUFFER",
    StationType.MARRIAGE_STATION: "MARRIAGE",
    StationType.CHARGING_STATION: "CHARGER",
}


def _station_name(station_type: StationType) -> str:
    return station_type.value.replace("_", " ").title()


def _runtime_stations(layout: LayoutVersionContent) -> list[Station]:
    return [
        Station(
            id=station.id,
            name=_station_name(station.type),
            type=STATION_RUNTIME_TYPES[station.type],
            x=station.x,
            y=station.y,
        )
        for station in layout.stations
    ]


def _spawn_points(layout: LayoutVersionContent, robot_count: int) -> list[tuple[float, float]]:
    charger = next(
        station for station in layout.stations if station.type == StationType.CHARGING_STATION
    )
    columns = min(10, robot_count)
    rows = math.ceil(robot_count / columns)
    spacing_x = min(1.2, layout.width / max(columns - 1, 1))
    spacing_y = min(1.2, layout.height / max(rows - 1, 1)) if rows > 1 else 0.0
    grid_width = (columns - 1) * spacing_x
    grid_height = (rows - 1) * spacing_y
    start_x = min(max(charger.x - grid_width / 2, 0.0), layout.width - grid_width)
    preferred_y = charger.y + 2.0
    start_y = min(max(preferred_y, 0.0), layout.height - grid_height)
    return [
        (start_x + index % columns * spacing_x, start_y + index // columns * spacing_y)
        for index in range(robot_count)
    ]


def _initial_robots(robot_count: int, layout: LayoutVersionContent) -> dict[str, Robot]:
    now = datetime.now(UTC)
    robots: dict[str, Robot] = {}
    for index, (x, y) in enumerate(_spawn_points(layout, robot_count)):
        robot_id = f"AMR-{index + 1:02d}"
        robots[robot_id] = Robot(
            id=robot_id,
            name=robot_id,
            status=RobotStatus.IDLE,
            pose=Pose(x=x, y=y, yaw=0.0),
            velocity=Velocity(linear=0.0, angular=0.0),
            battery=100.0,
            last_seen_at=now,
        )
    return robots


def _join_paths(
    first: tuple[tuple[float, float], ...],
    second: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    if first and second and first[-1] == second[0]:
        return (*first, *second[1:])
    return (*first, *second)


class FactoryState:
    """Sole owner of mutable factory runtime state.

    State is in-memory only for this sprint: a backend restart resets
    everything. Durable (PostgreSQL/TimescaleDB) persistence is a later phase.
    """

    def __init__(
        self,
        config: MockFactoryConfig,
        *,
        seed_mock_robots: bool = True,
        layout: LayoutVersionContent | None = None,
        route_id: str = DEFAULT_ROUTE_ID,
    ) -> None:
        self.config = config
        self._seed_mock_robots = seed_mock_robots
        self._layout = (layout or default_layout_content()).model_copy(deep=True)
        self._route_id = route_id
        self._active_scenario_id: str | None = None
        self.robots: dict[str, Robot] = {}
        self.stations: list[Station] = []
        self.tasks: dict[str, Task] = {}
        self.alerts: list[FactoryAlert] = []
        self.metrics: FactoryMetrics = _empty_metrics()
        self.initialize()

    def initialize(self) -> None:
        self.robots = (
            _initial_robots(self.config.robot_count, self._layout) if self._seed_mock_robots else {}
        )
        self.stations = _runtime_stations(self._layout)
        self.tasks = {}
        self.alerts = []
        self.metrics = _empty_metrics()
        logger.info("factory initialized with %d robots", len(self.robots))

    def reset(self) -> None:
        self.initialize()
        logger.info("factory reset")

    def get_layout(self) -> FactoryLayout:
        return FactoryLayout(
            width_m=self._layout.width,
            height_m=self._layout.height,
            stations=[station.model_copy(deep=True) for station in self.stations],
        )

    @property
    def layout(self) -> LayoutVersionContent:
        return self._layout.model_copy(deep=True)

    @property
    def route_id(self) -> str:
        return self._route_id

    @property
    def active_scenario_id(self) -> str | None:
        return self._active_scenario_id

    def set_active_scenario(self, scenario_id: str | None) -> None:
        self._active_scenario_id = scenario_id

    @property
    def delivery_route(self) -> LayoutRoute:
        route = next(
            (candidate for candidate in self._layout.routes if candidate.id == self._route_id),
            None,
        )
        if route is None:
            raise ValueError(f"Route '{self._route_id}' not found in active layout")
        if route.kind != RouteKind.DELIVERY:
            raise ValueError(f"Route '{self._route_id}' is not a delivery route")
        return route.model_copy(deep=True)

    def apply_layout(self, layout: LayoutVersionContent, route_id: str) -> None:
        route = next((candidate for candidate in layout.routes if candidate.id == route_id), None)
        if route is None:
            raise ValueError(f"Route '{route_id}' not found in applied layout")
        if route.kind != RouteKind.DELIVERY:
            raise ValueError(f"Route '{route_id}' is not a delivery route")
        self._layout = layout.model_copy(deep=True)
        self._route_id = route_id
        self.stations = _runtime_stations(self._layout)

    def validate_transport_route(
        self, pickup_station_id: str, dropoff_station_id: str
    ) -> None:
        station_ids = {station.id for station in self._layout.stations}
        unknown = [
            station_id
            for station_id in (pickup_station_id, dropoff_station_id)
            if station_id not in station_ids
        ]
        if unknown:
            raise ValueError(f"Unknown station in active layout: {', '.join(unknown)}")
        route = self.delivery_route
        if (route.start_station_id, route.end_station_id) != (
            pickup_station_id,
            dropoff_station_id,
        ):
            raise ValueError(
                f"Active route '{route.id}' does not serve "
                f"{pickup_station_id} -> {dropoff_station_id}"
            )

    def route_waypoints(self, route_key: tuple[str, str]) -> tuple[tuple[float, float], ...]:
        if route_key[0] == "ANY":
            charger = next(
                station
                for station in self._layout.stations
                if station.type == StationType.CHARGING_STATION
            )
            return ((charger.x, charger.y),)
        route = next(
            (
                candidate
                for candidate in self._layout.routes
                if candidate.start_station_id == route_key[0]
                and candidate.end_station_id == route_key[1]
            ),
            None,
        )
        if route is None:
            raise ValueError(f"Unknown route: {route_key}")
        return tuple((point.x, point.y) for point in route.waypoints)

    def task_route_waypoints(
        self,
        pose: Pose,
        pickup_station_id: str,
        dropoff_station_id: str,
    ) -> tuple[tuple[tuple[float, float], ...], int]:
        route = self.delivery_route
        if (route.start_station_id, route.end_station_id) != (
            pickup_station_id,
            dropoff_station_id,
        ):
            raise ValueError(
                f"Applied route '{route.id}' does not serve "
                f"{pickup_station_id} -> {dropoff_station_id}"
            )
        origin = min(
            self._layout.stations,
            key=lambda station: math.hypot(pose.x - station.x, pose.y - station.y),
        )
        approach = self._network_path(origin.id, pickup_station_id)
        delivery = tuple((point.x, point.y) for point in route.waypoints)
        return _join_paths(approach, delivery), len(approach)

    def charging_route_waypoints(self, pose: Pose) -> tuple[tuple[float, float], ...]:
        charger = next(
            station
            for station in self._layout.stations
            if station.type == StationType.CHARGING_STATION
        )
        origin = min(
            self._layout.stations,
            key=lambda station: math.hypot(pose.x - station.x, pose.y - station.y),
        )
        return self._network_path(origin.id, charger.id)

    def _network_path(
        self, start_station_id: str, end_station_id: str
    ) -> tuple[tuple[float, float], ...]:
        try:
            return shortest_station_path(self._layout, start_station_id, end_station_id)
        except ValueError:
            # Legacy v1/v2 layouts did not model support links. Preserve their
            # runtime behavior while v3+ layouts remain constrained to the network.
            target = next(
                station for station in self._layout.stations if station.id == end_station_id
            )
            logger.warning(
                "layout route network is disconnected; using legacy direct path %s -> %s",
                start_station_id,
                end_station_id,
            )
            return ((target.x, target.y),)

    def list_robots(self) -> list[Robot]:
        return [robot.model_copy(deep=True) for robot in self.robots.values()]

    def get_robot(self, robot_id: str) -> Robot | None:
        robot = self.robots.get(robot_id)
        return robot.model_copy(deep=True) if robot is not None else None

    def update_robot(self, robot: Robot) -> None:
        self.robots[robot.id] = robot.model_copy(deep=True)

    def synchronize_robot_registry(self, robot_ids: list[str]) -> bool:
        """Replace the edge registry while preserving telemetry for known robots."""

        if self._seed_mock_robots:
            return False
        previous_ids = set(self.robots)
        next_ids = set(robot_ids)
        if previous_ids == next_ids:
            return False

        epoch = datetime(1970, 1, 1, tzinfo=UTC)
        spawn_x, spawn_y = _spawn_points(self._layout, 1)[0]
        self.robots = {
            robot_id: self.robots.get(robot_id)
            or Robot(
                id=robot_id,
                name=robot_id,
                status=RobotStatus.OFFLINE,
                pose=Pose(x=spawn_x, y=spawn_y, yaw=0.0),
                velocity=Velocity(linear=0.0, angular=0.0),
                battery=0.0,
                last_seen_at=epoch,
            )
            for robot_id in robot_ids
        }
        logger.info("edge robot registry synchronized with %d robots", len(self.robots))
        return True

    def list_tasks(self) -> list[Task]:
        return [task.model_copy(deep=True) for task in self.tasks.values()]

    def get_task(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        return task.model_copy(deep=True) if task is not None else None

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task.model_copy(deep=True)

    def update_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task.model_copy(deep=True)

    def list_alerts(self) -> list[FactoryAlert]:
        return [alert.model_copy(deep=True) for alert in self.alerts]

    def add_alert(self, alert: FactoryAlert) -> None:
        self.alerts.append(alert.model_copy(deep=True))

    def get_metrics(self) -> FactoryMetrics:
        return self.metrics.model_copy(deep=True)

    def update_metrics(self, metrics: FactoryMetrics) -> None:
        self.metrics = metrics.model_copy(deep=True)


def get_factory_state(request: Request) -> FactoryState:
    return cast(FactoryState, request.app.state.factory_state)


FactoryStateDep = Annotated[FactoryState, Depends(get_factory_state)]
