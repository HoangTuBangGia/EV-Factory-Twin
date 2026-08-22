from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol


class TaskKpiRecord(Protocol):
    created_at: float
    started_at: float | None
    completed_at: float | None
    due_at: float
    travel_distance: float
    congestion_wait: float


@dataclass(frozen=True)
class AuthoritativeKpis:
    total_tasks: int
    completed_tasks: int
    unfinished_tasks: int
    completion_rate: float
    throughput_per_hour: float
    average_cycle_time: float
    average_waiting_time: float
    fleet_utilization_percent: float
    starvation_events: int
    congestion_percent: float
    travel_distance: float
    average_delivery_delay: float


def calculate_authoritative_kpis(
    records: Sequence[TaskKpiRecord],
    *,
    simulation_time: float,
    robot_count: int,
    robot_busy_time: float,
    starvation_threshold: float,
) -> AuthoritativeKpis:
    if not isfinite(simulation_time) or simulation_time <= 0.0:
        raise ValueError("simulation_time must be positive and finite")
    if robot_count <= 0:
        raise ValueError("robot_count must be positive")
    completed = [
        (record, record.completed_at) for record in records if record.completed_at is not None
    ]
    completed_count = len(completed)
    total = len(records)
    cycle_times = [completed_at - record.created_at for record, completed_at in completed]
    waiting_times = [
        (record.started_at - record.created_at) if record.started_at is not None else 0.0
        for record, _ in completed
    ]
    delays = [max(0.0, completed_at - record.due_at) for record, completed_at in completed]
    total_cycle = sum(cycle_times)
    congestion_wait = sum(record.congestion_wait for record, _ in completed)
    starvation = sum(
        1
        for record in records
        if record.created_at <= simulation_time
        if (
            (record.started_at - record.created_at)
            if record.started_at is not None
            else simulation_time - record.created_at
        )
        > starvation_threshold
    )

    def average(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return AuthoritativeKpis(
        total_tasks=total,
        completed_tasks=completed_count,
        unfinished_tasks=total - completed_count,
        completion_rate=completed_count / total if total else 0.0,
        throughput_per_hour=completed_count / (simulation_time / 3600.0),
        average_cycle_time=average(cycle_times),
        average_waiting_time=average(waiting_times),
        fleet_utilization_percent=min(
            100.0, max(0.0, robot_busy_time / (robot_count * simulation_time) * 100.0)
        ),
        starvation_events=starvation,
        congestion_percent=(congestion_wait / total_cycle * 100.0) if total_cycle else 0.0,
        travel_distance=sum(record.travel_distance for record, _ in completed),
        average_delivery_delay=average(delays),
    )
