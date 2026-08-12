from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    name: str = "default"
    num_robots: int = 3
    num_tasks: int = 10
    task_arrival_interval: float = 10.0
    travel_time: float = 30.0
    loading_time: float = 10.0
    simulation_time: float = 3600.0
