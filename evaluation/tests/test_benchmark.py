import pandas as pd
from ev_evaluation.benchmark import rank_scenarios


def test_rank_scenarios() -> None:
    data = pd.DataFrame(
        [
            {
                "scenario": "baseline",
                "throughput_per_hour": 213.0,
                "average_cycle_time": 1275.0,
                "average_waiting_time": 1225.0,
            },
            {
                "scenario": "congestion",
                "throughput_per_hour": 132.0,
                "average_cycle_time": 1477.5,
                "average_waiting_time": 1397.5,
            },
            {
                "scenario": "more_robots",
                "throughput_per_hour": 426.0,
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
