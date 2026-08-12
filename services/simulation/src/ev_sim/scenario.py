import json
from pathlib import Path

from ev_sim.config import SimulationConfig


def load_scenario(path: str | Path) -> SimulationConfig:
    scenario_path = Path(path)

    with scenario_path.open(encoding="utf-8") as file:
        data = json.load(file)

    return SimulationConfig(
        name=data["name"],
        num_robots=data["num_robots"],
        num_tasks=data["num_tasks"],
        task_arrival_interval=data["task_arrival_interval"],
        travel_time=data["travel_time"],
        loading_time=data["loading_time"],
        simulation_time=data["simulation_time"],
    )
