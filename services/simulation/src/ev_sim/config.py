from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SimulationConfig:
    name: str = "default"
    num_robots: int = 3
    num_tasks: int = 10
    task_arrival_interval: float = 10.0
    travel_time: float = 30.0
    loading_time: float = 10.0
    simulation_time: float = 3600.0

    def __post_init__(self) -> None:
        counts = {
            "num_robots": self.num_robots,
            "num_tasks": self.num_tasks,
        }
        for field_name, count_value in counts.items():
            if (
                isinstance(count_value, bool)
                or not isinstance(count_value, int)
                or count_value <= 0
            ):
                raise ValueError(f"{field_name} must be a positive integer")

        durations = {
            "task_arrival_interval": self.task_arrival_interval,
            "travel_time": self.travel_time,
            "loading_time": self.loading_time,
            "simulation_time": self.simulation_time,
        }
        for field_name, duration_value in durations.items():
            if (
                isinstance(duration_value, bool)
                or not isinstance(duration_value, (int, float))
                or not isfinite(duration_value)
                or duration_value <= 0
            ):
                raise ValueError(f"{field_name} must be a positive finite number")
