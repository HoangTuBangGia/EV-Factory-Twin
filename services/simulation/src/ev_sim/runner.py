import argparse

import simpy

from ev_sim.config import SimulationConfig
from ev_sim.metrics import calculate_metrics
from ev_sim.model import FactorySimulation, TaskRecord
from ev_sim.scenario import load_scenario


def task_generator(
    env: simpy.Environment,
    simulation: FactorySimulation,
    config: SimulationConfig,
):
    for task_id in range(config.num_tasks):
        env.process(simulation.process_task(task_id))
        yield env.timeout(config.task_arrival_interval)


def run_simulation(config: SimulationConfig) -> list[TaskRecord]:
    env = simpy.Environment()

    simulation = FactorySimulation(
        env=env,
        num_robots=config.num_robots,
        travel_time=config.travel_time,
        loading_time=config.loading_time,
    )

    env.process(task_generator(env, simulation, config))
    env.run(until=config.simulation_time)

    return simulation.records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        type=str,
        default="services/simulation/scenarios/baseline.json",
    )
    args = parser.parse_args()

    config = load_scenario(args.scenario)
    records = run_simulation(config)

    metrics = calculate_metrics(
        records,
        simulation_time=config.simulation_time,
        total_tasks=config.num_tasks,
    )

    print(f"=== SCENARIO: {config.name} ===")
    print(f"Robots: {config.num_robots}")
    print(f"Requested tasks: {metrics.total_tasks}")
    print(f"Completed tasks: {metrics.completed_tasks}")
    print(f"Backlog: {metrics.unfinished_tasks}")
    print(f"Completion rate: {metrics.completion_rate:.2%}")
    print(f"Throughput: {metrics.throughput_per_hour:.2f} tasks/hour")
    print(f"Average cycle time: {metrics.average_cycle_time:.2f}s")
    print(f"Average waiting time: {metrics.average_waiting_time:.2f}s")


if __name__ == "__main__":
    main()
