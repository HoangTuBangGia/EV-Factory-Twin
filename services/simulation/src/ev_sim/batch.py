import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from ev_sim.metrics import calculate_metrics
from ev_sim.runner import run_simulation
from ev_sim.scenario import load_scenario


def run_batch(
    scenarios_dir: Path,
    output_dir: Path,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    scenario_paths = sorted(scenarios_dir.glob("*.json"))

    for scenario_path in scenario_paths:
        config = load_scenario(scenario_path)

        records = run_simulation(config)

        metrics = calculate_metrics(
            records,
            simulation_time=config.simulation_time,
            total_tasks=config.num_tasks,
        )

        result = {
            "scenario": config.name,
            "num_robots": config.num_robots,
            **asdict(metrics),
        }

        results.append(result)

    output_dir.mkdir(parents=True, exist_ok=True)

    write_json(results, output_dir / "simulation_results.json")
    write_csv(results, output_dir / "simulation_results.csv")

    return results


def write_json(
    results: list[dict[str, object]],
    path: Path,
) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)


def write_csv(
    results: list[dict[str, object]],
    path: Path,
) -> None:
    if not results:
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=Path("services/simulation/scenarios"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/datasets"),
    )

    args = parser.parse_args()

    results = run_batch(
        scenarios_dir=args.scenarios_dir,
        output_dir=args.output_dir,
    )

    print(f"Ran {len(results)} scenarios.")

    for result in results:
        print(
            f"{result['scenario']}: "
            f"throughput={result['throughput_per_hour']}, "
            f"cycle={result['average_cycle_time']}"
        )


if __name__ == "__main__":
    main()
