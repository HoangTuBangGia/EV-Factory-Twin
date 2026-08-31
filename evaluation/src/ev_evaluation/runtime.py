import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from twin_core.collision import colliding_robot_pairs

REQUIRED_COLUMNS = {"robot_id", "source_timestamp", "ingested_at", "pose"}


def summarize_runtime(samples: pd.DataFrame) -> dict[str, float | int]:
    missing = REQUIRED_COLUMNS - set(samples.columns)
    if missing:
        raise ValueError(f"telemetry CSV missing columns: {', '.join(sorted(missing))}")
    accepted = samples.loc[
        samples.get("ordering_status", pd.Series("ACCEPTED", index=samples.index)) == "ACCEPTED"
    ].copy()
    if accepted.empty:
        raise ValueError("telemetry CSV contains no accepted samples")
    accepted["source_timestamp"] = pd.to_datetime(accepted["source_timestamp"], utc=True)
    accepted["ingested_at"] = pd.to_datetime(accepted["ingested_at"], utc=True)
    latency_ms = (
        accepted["ingested_at"] - accepted["source_timestamp"]
    ).dt.total_seconds().to_numpy() * 1000.0

    positions: dict[str, tuple[float, float]] = {}
    active_pairs: set[tuple[str, str]] = set()
    collision_events = 0
    for row in accepted.sort_values("source_timestamp").itertuples(index=False):
        if isinstance(row.pose, dict):
            pose = row.pose
        elif isinstance(row.pose, (str, bytes, bytearray)):
            pose = json.loads(row.pose)
            if not isinstance(pose, dict):
                raise ValueError("telemetry pose must be a JSON object")
        else:
            raise ValueError("telemetry pose must be a JSON object")
        positions[str(row.robot_id)] = (float(pose["x"]), float(pose["y"]))
        pairs = colliding_robot_pairs(positions)
        collision_events += len(pairs - active_pairs)
        active_pairs = pairs

    rates = []
    for _, robot_samples in accepted.groupby("robot_id"):
        duration = (
            robot_samples["source_timestamp"].max() - robot_samples["source_timestamp"].min()
        ).total_seconds()
        if duration > 0.0:
            rates.append((len(robot_samples) - 1) / duration)
    observation_seconds = (
        accepted["source_timestamp"].max() - accepted["source_timestamp"].min()
    ).total_seconds()
    return {
        "samples": len(accepted),
        "robots": int(accepted["robot_id"].nunique()),
        "latency_p50_ms": float(np.percentile(latency_ms, 50)),
        "latency_p95_ms": float(np.percentile(latency_ms, 95)),
        "latency_max_ms": float(np.max(latency_ms)),
        "mean_update_rate_hz": float(np.mean(rates)) if rates else 0.0,
        "observation_duration_seconds": observation_seconds,
        "collision_events": collision_events,
        "collision_events_per_hour": (
            collision_events / (observation_seconds / 3600.0) if observation_seconds > 0.0 else 0.0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize recorded live telemetry performance")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/reports/runtime_performance.json"),
    )
    args = parser.parse_args()
    summary = summarize_runtime(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
