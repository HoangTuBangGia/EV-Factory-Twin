import pytest
from ev_sim.logistics import LogisticsConfig, run_logistics_simulation


def config(**updates: object) -> LogisticsConfig:
    values: dict[str, object] = {
        "robot_count": 1,
        "task_count": 1,
        "demand_interval_seconds": 10.0,
        "route_distance_m": 10.0,
        "robot_speed_mps": 1.0,
        "loading_time_seconds": 2.0,
        "simulation_time_seconds": 100.0,
        "charger_count": 1,
    }
    values.update(updates)
    return LogisticsConfig(**values)  # type: ignore[arg-type]


def test_robot_charges_before_delivery_when_battery_is_below_reserve() -> None:
    result = run_logistics_simulation(config(initial_battery_percent=10.0))

    assert result.records[0].completed_at == 54.0
    assert result.robots[0].charging_time == 40.0
    assert result.robots[0].battery_percent == 89.5
    assert result.metrics.completion_rate == 1.0
    assert result.metrics.travel_distance == 10.0


def test_route_contention_is_reported_as_congestion() -> None:
    result = run_logistics_simulation(
        config(robot_count=2, task_count=2, demand_interval_seconds=0.1)
    )

    assert result.metrics.completed_tasks == 2
    assert result.records[1].congestion_wait == pytest.approx(9.9)
    assert result.metrics.congestion_percent > 0.0


def test_unfinished_robot_time_counts_toward_utilization() -> None:
    result = run_logistics_simulation(config(simulation_time_seconds=5.0))

    assert result.metrics.completed_tasks == 0
    assert result.metrics.fleet_utilization_percent == 100.0
