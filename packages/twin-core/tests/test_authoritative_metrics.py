from dataclasses import dataclass

import pytest
from twin_core.metrics.authoritative import calculate_authoritative_kpis


@dataclass
class Record:
    created_at: float
    started_at: float | None
    completed_at: float | None
    due_at: float
    travel_distance: float
    congestion_wait: float


def test_calculates_all_authoritative_kpis() -> None:
    metrics = calculate_authoritative_kpis(
        [
            Record(0.0, 10.0, 50.0, 40.0, 30.0, 5.0),
            Record(20.0, None, None, 60.0, 0.0, 0.0),
        ],
        simulation_time=100.0,
        robot_count=2,
        robot_busy_time=80.0,
        starvation_threshold=60.0,
    )

    assert metrics.completed_tasks == 1
    assert metrics.unfinished_tasks == 1
    assert metrics.completion_rate == 0.5
    assert metrics.throughput_per_hour == 36.0
    assert metrics.average_cycle_time == 50.0
    assert metrics.average_waiting_time == 10.0
    assert metrics.fleet_utilization_percent == 40.0
    assert metrics.starvation_events == 1
    assert metrics.congestion_percent == 10.0
    assert metrics.travel_distance == 30.0
    assert metrics.average_delivery_delay == 10.0


def test_rejects_invalid_kpi_denominators() -> None:
    with pytest.raises(ValueError, match="simulation_time"):
        calculate_authoritative_kpis(
            [],
            simulation_time=0.0,
            robot_count=1,
            robot_busy_time=0.0,
            starvation_threshold=1.0,
        )
