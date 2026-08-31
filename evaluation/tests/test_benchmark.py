import pandas as pd
import pytest
from ev_evaluation.benchmark import rank_scenarios
from ev_evaluation.runtime import summarize_runtime


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


def test_runtime_summary_measures_latency_rate_and_collision_entries() -> None:
    samples = pd.DataFrame(
        [
            {
                "robot_id": "AMR-01",
                "source_timestamp": "2026-01-01T00:00:00Z",
                "ingested_at": "2026-01-01T00:00:00.010Z",
                "pose": '{"x":0,"y":0}',
                "ordering_status": "ACCEPTED",
            },
            {
                "robot_id": "AMR-02",
                "source_timestamp": "2026-01-01T00:00:00Z",
                "ingested_at": "2026-01-01T00:00:00.020Z",
                "pose": '{"x":2,"y":0}',
                "ordering_status": "ACCEPTED",
            },
            {
                "robot_id": "AMR-01",
                "source_timestamp": "2026-01-01T00:00:01Z",
                "ingested_at": "2026-01-01T00:00:01.010Z",
                "pose": '{"x":1.5,"y":0}',
                "ordering_status": "ACCEPTED",
            },
            {
                "robot_id": "AMR-02",
                "source_timestamp": "2026-01-01T00:00:01Z",
                "ingested_at": "2026-01-01T00:00:01.020Z",
                "pose": '{"x":2,"y":0}',
                "ordering_status": "ACCEPTED",
            },
        ]
    )

    summary = summarize_runtime(samples)

    assert summary["samples"] == 4
    assert summary["robots"] == 2
    assert summary["latency_p50_ms"] == pytest.approx(15.0)
    assert summary["mean_update_rate_hz"] == 1.0
    assert summary["observation_duration_seconds"] == 1.0
    assert summary["collision_events"] == 1
    assert summary["collision_events_per_hour"] == 3600.0
