from dataclasses import dataclass
from math import isfinite

import simpy
from twin_core.metrics.authoritative import AuthoritativeKpis, calculate_authoritative_kpis


@dataclass(frozen=True)
class LogisticsConfig:
    robot_count: int
    task_count: int
    demand_interval_seconds: float
    route_distance_m: float
    robot_speed_mps: float
    loading_time_seconds: float
    simulation_time_seconds: float
    charger_count: int
    congestion_multiplier: float = 1.0
    route_capacity: int = 1
    initial_battery_percent: float = 80.0
    battery_consumption_percent_per_meter: float = 0.05
    battery_reserve_percent: float = 10.0
    charge_target_percent: float = 90.0
    charge_rate_percent_per_second: float = 2.0
    starvation_threshold_seconds: float = 120.0

    def __post_init__(self) -> None:
        counts = (self.robot_count, self.task_count, self.charger_count, self.route_capacity)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in counts
        ):
            raise ValueError("robot/task/charger/route capacities must be positive integers")
        positive = (
            self.demand_interval_seconds,
            self.route_distance_m,
            self.robot_speed_mps,
            self.loading_time_seconds,
            self.simulation_time_seconds,
            self.charge_rate_percent_per_second,
            self.starvation_threshold_seconds,
        )
        if any(not isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("simulation durations, distance, speed and rate must be positive")
        if not 1.0 <= self.congestion_multiplier <= 10.0:
            raise ValueError("congestion_multiplier must be in [1, 10]")
        if not 0.0 <= self.initial_battery_percent <= 100.0:
            raise ValueError("initial battery must be in [0, 100]")


@dataclass
class RobotState:
    robot_id: int
    battery_percent: float
    busy_time: float = 0.0
    charging_time: float = 0.0
    busy_started_at: float | None = None


@dataclass
class LogisticsTaskRecord:
    task_id: int
    created_at: float
    due_at: float
    started_at: float | None = None
    completed_at: float | None = None
    travel_distance: float = 0.0
    congestion_wait: float = 0.0
    charging_wait: float = 0.0


@dataclass(frozen=True)
class LogisticsResult:
    records: list[LogisticsTaskRecord]
    robots: list[RobotState]
    metrics: AuthoritativeKpis


class LogisticsSimulation:
    def __init__(self, env: simpy.Environment, config: LogisticsConfig) -> None:
        self.env = env
        self.config = config
        self.robots = [
            RobotState(robot_id=index + 1, battery_percent=config.initial_battery_percent)
            for index in range(config.robot_count)
        ]
        self.available_robots = simpy.Store(env, capacity=config.robot_count)
        for robot in self.robots:
            self.available_robots.put(robot)
        self.chargers = simpy.Resource(env, capacity=config.charger_count)
        self.route = simpy.Resource(env, capacity=config.route_capacity)
        base_service = (
            2.0 * config.loading_time_seconds + config.route_distance_m / config.robot_speed_mps
        )
        self.records = [
            LogisticsTaskRecord(
                task_id=index + 1,
                created_at=index * config.demand_interval_seconds,
                due_at=index * config.demand_interval_seconds + base_service,
            )
            for index in range(config.task_count)
        ]

    def generate(self):
        for record in self.records:
            self.env.process(self.process(record))
            yield self.env.timeout(self.config.demand_interval_seconds)

    def process(self, record: LogisticsTaskRecord):
        robot: RobotState = yield self.available_robots.get()
        record.started_at = self.env.now
        busy_started = self.env.now
        robot.busy_started_at = busy_started
        required_energy = (
            self.config.route_distance_m * self.config.battery_consumption_percent_per_meter
        )
        if robot.battery_percent < required_energy + self.config.battery_reserve_percent:
            charge_wait_started = self.env.now
            with self.chargers.request() as charger_request:
                yield charger_request
                record.charging_wait = self.env.now - charge_wait_started
                charge_duration = (
                    self.config.charge_target_percent - robot.battery_percent
                ) / self.config.charge_rate_percent_per_second
                if charge_duration > 0.0:
                    yield self.env.timeout(charge_duration)
                    robot.charging_time += charge_duration
                    robot.battery_percent = self.config.charge_target_percent

        yield self.env.timeout(self.config.loading_time_seconds)
        congestion_started = self.env.now
        with self.route.request() as route_request:
            yield route_request
            route_wait = self.env.now - congestion_started
            base_travel_time = self.config.route_distance_m / self.config.robot_speed_mps
            travel_time = base_travel_time * self.config.congestion_multiplier
            record.congestion_wait = route_wait + travel_time - base_travel_time
            yield self.env.timeout(travel_time)
        yield self.env.timeout(self.config.loading_time_seconds)

        robot.battery_percent = max(0.0, robot.battery_percent - required_energy)
        robot.busy_time += self.env.now - busy_started
        robot.busy_started_at = None
        record.travel_distance = self.config.route_distance_m
        record.completed_at = self.env.now
        yield self.available_robots.put(robot)


def run_logistics_simulation(config: LogisticsConfig) -> LogisticsResult:
    env = simpy.Environment()
    simulation = LogisticsSimulation(env, config)
    env.process(simulation.generate())
    env.run(until=config.simulation_time_seconds)
    busy_time = sum(
        robot.busy_time
        + (
            config.simulation_time_seconds - robot.busy_started_at
            if robot.busy_started_at is not None
            else 0.0
        )
        for robot in simulation.robots
    )
    metrics = calculate_authoritative_kpis(
        simulation.records,
        simulation_time=config.simulation_time_seconds,
        robot_count=config.robot_count,
        robot_busy_time=busy_time,
        starvation_threshold=config.starvation_threshold_seconds,
    )
    return LogisticsResult(simulation.records, simulation.robots, metrics)
