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
