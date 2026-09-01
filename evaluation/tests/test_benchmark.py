import pandas as pd
from ev_evaluation.benchmark import rank_scenarios


def test_rank_scenarios() -> None:
    data = pd.DataFrame(
        [
            {
                "scenario": "baseline",
                "completion_rate": 0.8,
                "throughput_per_hour": 213.0,
                "unfinished_tasks": 100,
                "average_cycle_time": 1275.0,
                "average_waiting_time": 1225.0,
            },
            {
                "scenario": "congestion",
                "completion_rate": 0.8,
                "throughput_per_hour": 132.0,
                "unfinished_tasks": 100,
                "average_cycle_time": 1477.5,
                "average_waiting_time": 1397.5,
            },
            {
                "scenario": "more_robots",
                "completion_rate": 0.95,
                "throughput_per_hour": 426.0,
                "unfinished_tasks": 25,
                "average_cycle_time": 750.0,
                "average_waiting_time": 700.0,
            },
        ]
    )

    ranked = rank_scenarios(data)

    assert ranked.iloc[0]["scenario"] == "more_robots"
    assert ranked.iloc[1]["scenario"] == "baseline"
    assert ranked.iloc[2]["scenario"] == "congestion"

    assert ranked.iloc[0]["rank"] == 1
    assert ranked.iloc[1]["rank"] == 2
    assert ranked.iloc[2]["rank"] == 3


def test_rank_scenarios_prefers_completion_before_raw_throughput() -> None:
    data = pd.DataFrame(
        [
            {
                "scenario": "high-throughput-backlog",
                "completion_rate": 0.7,
                "throughput_per_hour": 500.0,
                "unfinished_tasks": 300,
                "average_cycle_time": 30.0,
                "average_waiting_time": 5.0,
            },
            {
                "scenario": "completed-flow",
                "completion_rate": 0.95,
                "throughput_per_hour": 400.0,
                "unfinished_tasks": 50,
                "average_cycle_time": 40.0,
                "average_waiting_time": 8.0,
            },
        ]
    )

    ranked = rank_scenarios(data)

    assert ranked.iloc[0]["scenario"] == "completed-flow"
