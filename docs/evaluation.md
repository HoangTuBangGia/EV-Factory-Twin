# Simulation & Evaluation

## Purpose

The SimPy simulation module provides a discrete-event benchmark for EV factory
logistics KPIs such as throughput, cycle time, waiting time, backlog, and
completion rate. It is intended for fast multi-scenario comparison under AR-01,
including changes in robot count, route time, and demand pressure.

This SimPy benchmark does not replace Gazebo or ROS2. The main physical
simulation architecture remains Gazebo -> ROS2 -> FastAPI -> WebSocket -> React.
SimPy is used here only as a lightweight KPI benchmark layer, while Gazebo/ROS2
remain the primary physical simulation and telemetry source for the product.

## Prerequisites

- Python 3.12
- uv

## Environment Setup

```powershell
uv sync --all-packages --dev
```

The standalone SimPy simulation does not currently require an OpenAI API key or
database connection.

## Single Scenario Run

Run one scenario JSON file with:

```powershell
uv run --package ev-factory-simulation python -m ev_sim.runner --scenario services/simulation/scenarios/baseline.json
```

You can replace the scenario path with any JSON scenario file under
`services/simulation/scenarios`.

## Batch Run

Run all scenarios and generate benchmark outputs with:

```powershell
.\scripts\evaluate.ps1
```

The script runs the simulation batch first, then ranks the generated results.

## KPI Definitions

- Throughput = completed tasks / simulation hours
- Cycle Time = completed_at - created_at
- Waiting Time = started_at - created_at
- Backlog = total_tasks - completed_tasks
- Completion Rate = completed_tasks / total_tasks

## Scenario Definitions

- baseline: 3 robots, normal route, shared demand profile
- more_robots: 6 robots, same route and demand as baseline
- congestion: 3 robots, same demand as baseline, longer travel time to model a
  worse layout or congested route

## Benchmark Logic

Scenarios are ranked by:

1. Higher throughput
2. Lower cycle time
3. Lower waiting time

This ranking favors scenarios that complete more logistics tasks within the same
simulation horizon, then uses lower cycle and waiting time as tie-breakers.

## Output Files

- `evaluation/datasets/simulation_results.csv`
- `evaluation/datasets/simulation_results.json`
- `evaluation/reports/benchmark_summary.csv`

## Tests

Run the full test suite with:

```powershell
uv run pytest
```

## Limitations

- Does not model physical robot dynamics
- Does not consume ROS2/Gazebo telemetry yet
- Travel and loading times are deterministic
- SimPy is used only for quick KPI and benchmark evaluation
