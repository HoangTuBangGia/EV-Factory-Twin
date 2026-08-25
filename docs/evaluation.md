# Simulation & Evaluation

## Purpose

The MVP evaluation covers both the ROS2/Gazebo live path and the SimPy what-if path.
The SimPy simulation module provides a discrete-event benchmark for EV factory
logistics KPIs such as throughput, cycle time, waiting time, backlog, and
completion rate. It is intended for fast multi-scenario comparison under AR-01,
including changes in robot count, route time, and demand pressure.

This SimPy benchmark does not replace Gazebo or ROS2. The main physical path is
Gazebo -> ROS2 -> fleet/task manager -> telemetry bridge -> FastAPI -> WebSocket ->
Three.js. SimPy is the lightweight what-if and layout comparison layer, while
Gazebo/ROS2 remain the primary live simulation and telemetry source.

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

## Manual evaluation evidence

The recorded MVP evaluation, actual observed outputs, and timestamped screenshots
are documented in
[`evaluation/reports/manual_eval_evidence.md`](../evaluation/reports/manual_eval_evidence.md).
The report contains seven manual test cases covering realtime monitoring,
scenario benchmarking, the Monitor review workflow, factory apply, and persisted
workflow state.

## Tests

Run the full test suite with:

```powershell
uv run pytest
```

## MVP ROS2 acceptance

The evaluation is incomplete unless it demonstrates:

- at least two AMRs running in Gazebo/Nav2;
- telemetry received by FastAPI and rendered in the same 3D scene as mock data;
- a backend task/command reaching the ROS2 fleet/task manager;
- an abnormal condition producing a visible alert;
- a layout candidate changing at least travel time, congestion or throughput;
- Designer/Monitor approval before applying the candidate;
- measured ROS-to-backend and backend-to-browser latency plus basic FPS.

Run and record this hosted path with `docs/runbooks/mvp-edge-acceptance.md`.
Backend/DB, frontend, ROS and container CI are necessary gates but do not replace
the networked acceptance run against Cloud Run, Cloud SQL and the GCE edge.

## Limitations

- Does not model physical robot dynamics
- Does not model production-grade robot dynamics or fleet optimization
- Travel and loading times are deterministic
- SimPy is used only for quick KPI and layout benchmark evaluation
- Incident replay UI đầy đủ và retention vượt policy 30/90 ngày nằm ngoài MVP
