from dataclasses import dataclass

from ev_sim.model import TaskRecord


@dataclass(frozen=True)
class SimulationMetrics:
    total_tasks: int
    completed_tasks: int
    unfinished_tasks: int
    completion_rate: float
    throughput_per_hour: float
    average_cycle_time: float
    average_waiting_time: float


def calculate_metrics(
    records: list[TaskRecord],
    simulation_time: float,
    total_tasks: int | None = None,
) -> SimulationMetrics:
    completed_tasks = len(records)

    if total_tasks is None:
        total_tasks = completed_tasks

    unfinished_tasks = total_tasks - completed_tasks

    if completed_tasks == 0:
        return SimulationMetrics(
            total_tasks=total_tasks,
            completed_tasks=0,
            unfinished_tasks=unfinished_tasks,
            completion_rate=0.0,
            throughput_per_hour=0.0,
            average_cycle_time=0.0,
            average_waiting_time=0.0,
        )

    simulation_hours = simulation_time / 3600.0

    average_cycle_time = sum(record.cycle_time for record in records) / completed_tasks
    average_waiting_time = sum(record.waiting_time for record in records) / completed_tasks

    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

    return SimulationMetrics(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        unfinished_tasks=unfinished_tasks,
        completion_rate=completion_rate,
        throughput_per_hour=completed_tasks / simulation_hours,
        average_cycle_time=average_cycle_time,
        average_waiting_time=average_waiting_time,
    )
