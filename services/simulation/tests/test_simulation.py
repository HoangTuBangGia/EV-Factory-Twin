from collections.abc import Callable

import pytest
from ev_sim.config import SimulationConfig
from ev_sim.metrics import calculate_metrics
from ev_sim.runner import run_simulation


def test_simulation_completes_all_tasks() -> None:
    config = SimulationConfig(
        num_robots=3,
        num_tasks=10,
        task_arrival_interval=10.0,
        travel_time=30.0,
        loading_time=10.0,
        simulation_time=3600.0,
    )

    records = run_simulation(config)

    assert len(records) == 10


def test_task_cycle_time_and_waiting_time() -> None:
    config = SimulationConfig(
        num_robots=1,
        num_tasks=2,
        task_arrival_interval=10.0,
        travel_time=30.0,
        loading_time=10.0,
        simulation_time=3600.0,
    )

    records = run_simulation(config)

    assert records[0].cycle_time == 50.0
    assert records[0].waiting_time == 0.0

    assert records[1].cycle_time == 90.0
    assert records[1].waiting_time == 40.0


def test_metrics_are_calculated_correctly() -> None:
    config = SimulationConfig(
        num_robots=3,
        num_tasks=10,
        task_arrival_interval=10.0,
        travel_time=30.0,
        loading_time=10.0,
        simulation_time=3600.0,
    )

    records = run_simulation(config)
    metrics = calculate_metrics(records, config.simulation_time, total_tasks=config.num_tasks)

    assert metrics.total_tasks == 10
    assert metrics.completed_tasks == 10
    assert metrics.unfinished_tasks == 0
    assert metrics.completion_rate == 1.0
    assert metrics.throughput_per_hour == 10.0
    assert metrics.average_cycle_time == 74.0
    assert metrics.average_waiting_time == 24.0


def test_zero_completed_tasks_returns_zero_metrics() -> None:
    metrics = calculate_metrics([], 3600.0, total_tasks=10)

    assert metrics.total_tasks == 10
    assert metrics.completed_tasks == 0
    assert metrics.unfinished_tasks == 10
    assert metrics.completion_rate == 0.0
    assert metrics.throughput_per_hour == 0.0
    assert metrics.average_cycle_time == 0.0
    assert metrics.average_waiting_time == 0.0


def test_short_simulation_returns_backlog_without_crashing() -> None:
    config = SimulationConfig(
        num_robots=1,
        num_tasks=3,
        task_arrival_interval=1.0,
        travel_time=30.0,
        loading_time=10.0,
        simulation_time=1.0,
    )

    records = run_simulation(config)
    metrics = calculate_metrics(records, config.simulation_time, config.num_tasks)

    assert records == []
    assert metrics.completed_tasks == 0
    assert metrics.unfinished_tasks == 3
    assert metrics.throughput_per_hour == 0.0


def test_metrics_include_backlog() -> None:
    config = SimulationConfig(
        num_robots=3,
        num_tasks=500,
        task_arrival_interval=5.0,
        travel_time=30.0,
        loading_time=10.0,
        simulation_time=3600.0,
    )

    records = run_simulation(config)

    metrics = calculate_metrics(
        records,
        config.simulation_time,
        total_tasks=config.num_tasks,
    )

    assert metrics.total_tasks == 500
    assert metrics.completed_tasks == 213
    assert metrics.unfinished_tasks == 287
    assert metrics.completion_rate == 213 / 500
    assert metrics.throughput_per_hour == 213.0
    assert metrics.average_cycle_time == 1275.0
    assert metrics.average_waiting_time == 1225.0


def test_simulation_is_deterministic_for_the_same_config() -> None:
    config = SimulationConfig(
        name="deterministic",
        num_robots=2,
        num_tasks=20,
        task_arrival_interval=5.0,
        travel_time=20.0,
        loading_time=5.0,
        simulation_time=600.0,
    )

    first_records = run_simulation(config)
    second_records = run_simulation(config)

    assert first_records == second_records
    assert calculate_metrics(
        first_records, config.simulation_time, config.num_tasks
    ) == calculate_metrics(second_records, config.simulation_time, config.num_tasks)


@pytest.mark.parametrize(
    ("build_config", "field_name"),
    [
        pytest.param(lambda: SimulationConfig(num_robots=0), "num_robots", id="zero-robots"),
        pytest.param(lambda: SimulationConfig(num_robots=-1), "num_robots", id="negative-robots"),
        pytest.param(lambda: SimulationConfig(num_tasks=0), "num_tasks", id="zero-tasks"),
        pytest.param(lambda: SimulationConfig(num_tasks=-1), "num_tasks", id="negative-tasks"),
        pytest.param(
            lambda: SimulationConfig(task_arrival_interval=0),
            "task_arrival_interval",
            id="zero-arrival-interval",
        ),
        pytest.param(lambda: SimulationConfig(travel_time=-1), "travel_time", id="travel-time"),
        pytest.param(lambda: SimulationConfig(loading_time=0), "loading_time", id="loading-time"),
        pytest.param(
            lambda: SimulationConfig(simulation_time=0),
            "simulation_time",
            id="zero-simulation-time",
        ),
        pytest.param(
            lambda: SimulationConfig(simulation_time=float("inf")),
            "simulation_time",
            id="infinite-simulation-time",
        ),
        pytest.param(
            lambda: SimulationConfig(travel_time=float("nan")),
            "travel_time",
            id="nan-travel-time",
        ),
    ],
)
def test_config_rejects_invalid_counts_and_times(
    build_config: Callable[[], SimulationConfig],
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        build_config()


@pytest.mark.parametrize("simulation_time", [0.0, -1.0, float("inf"), float("nan")])
def test_metrics_reject_nonpositive_or_nonfinite_simulation_time(
    simulation_time: float,
) -> None:
    with pytest.raises(ValueError, match="simulation_time"):
        calculate_metrics([], simulation_time, total_tasks=10)


def test_metrics_reject_inconsistent_total_tasks() -> None:
    config = SimulationConfig(num_robots=1, num_tasks=1, simulation_time=100.0)
    records = run_simulation(config)

    with pytest.raises(ValueError, match="less than completed"):
        calculate_metrics(records, config.simulation_time, total_tasks=0)


@pytest.mark.parametrize("total_tasks", [-1, 1.5, True])
def test_metrics_reject_invalid_total_tasks(total_tasks: object) -> None:
    with pytest.raises(ValueError, match="total_tasks"):
        calculate_metrics([], 3600.0, total_tasks=total_tasks)  # type: ignore[arg-type]
