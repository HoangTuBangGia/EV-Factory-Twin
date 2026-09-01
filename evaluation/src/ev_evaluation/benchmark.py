import argparse
from pathlib import Path

import pandas as pd


def load_results(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def rank_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.copy()

    ranked = ranked.sort_values(
        by=[
            "completion_rate",
            "throughput_per_hour",
            "unfinished_tasks",
            "average_cycle_time",
            "average_waiting_time",
        ],
        ascending=[False, False, True, True, True],
    )

    ranked.insert(
        0,
        "rank",
        range(1, len(ranked) + 1),
    )

    return ranked


def save_report(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("evaluation/datasets/simulation_results.csv"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/reports/benchmark_summary.csv"),
    )

    args = parser.parse_args()

    results = load_results(args.input)
    ranked = rank_scenarios(results)

    save_report(
        ranked,
        args.output,
    )

    columns = [
        "rank",
        "scenario",
        "completion_rate",
        "throughput_per_hour",
        "unfinished_tasks",
        "average_cycle_time",
        "average_waiting_time",
    ]

    print("=== BENCHMARK RANKING ===")
    print(
        ranked[columns].to_string(
            index=False,
        )
    )


if __name__ == "__main__":
    main()
