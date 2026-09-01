# Simulation and Evaluation

## Evaluation boundary

The current MVP has two complementary simulation paths:

```text
What-if:  Immutable layout → SimPy → KPI → Compare → Human approval
Realtime: Gazebo ↔ ROS 2 ↔ Edge bridge ↔ FastAPI ↔ WebSocket ↔ Three.js
```

SimPy evaluates factory-flow alternatives quickly. Gazebo/ROS 2 validates the
robotics runtime and realtime integration. Neither path is evidence for the
other, and fixture/mock output is not accepted as hosted ROS evidence.

The canonical evaluation workspace and evidence policy are documented in
[`evaluation/README.md`](../evaluation/README.md). The current acceptance record
is [`evaluation/reports/mvp-acceptance.md`](../evaluation/reports/mvp-acceptance.md).

## Authoritative scenario metrics

The product computes KPI in `twin-core`; the frontend only presents them.

| Metric | Definition / interpretation |
|---|---|
| Completed tasks | Tasks completed within the simulation horizon |
| Unfinished tasks | Total tasks minus completed tasks |
| Completion rate | Completed tasks divided by total tasks |
| Throughput | Completed tasks divided by simulation hours |
| Average cycle time | Mean `completed_at - created_at` for completed tasks |
| Average waiting time | Mean `started_at - created_at` for completed tasks |
| Fleet utilization | Robot busy time divided by available fleet time |
| Starvation events | Tasks waiting longer than the authoritative threshold |
| Congestion percent | Congestion waiting divided by completed-task cycle time |
| Travel distance | Sum of completed-task travel distance |
| Average delivery delay | Mean positive lateness beyond task due time |

The API scenario path resolves route distance and congestion from the referenced
immutable `(layout_id, layout_version)`. Client-entered legacy travel assumptions
are not authoritative for a persisted scenario.

## Layout-aware what-if acceptance

A valid comparison must:

1. reference an immutable layout version;
2. use a delivery route whose station endpoints and waypoints validate;
3. derive travel distance and congestion from layout geometry;
4. present baseline and candidate geometry plus KPI;
5. keep optimization deterministic and bounded to at most 64 candidates;
6. require Designer submission and separate Monitor approval;
7. apply only after the edge command reports a positive terminal result.

Backend optimization ranks candidates by completion rate and throughput first,
then delivery delay, starvation, congestion, cycle time, utilization, travel
distance and resource cost. This API ranking is authoritative for the product.

## Standalone SimPy regression benchmark

The standalone pipeline remains a small deterministic regression tool for the
legacy JSON fixtures under `services/simulation/scenarios/`. It is not the
product's layout editor or hosted acceptance path.

Run it from the repository root:

```bash
uv run --package ev-factory-simulation python -m ev_sim.batch
uv run --package ev-twin-evaluation python -m ev_evaluation.benchmark
```

Generated outputs are intentionally untracked:

- `evaluation/datasets/simulation_results.json`
- `evaluation/datasets/simulation_results.csv`
- `evaluation/reports/benchmark_summary.csv`

The standalone evaluator orders completion rate and throughput first, followed
by unfinished work, cycle time and waiting time. Do not present this reduced
fixture metric set as the complete API KPI contract.

## Hosted ROS 2/Gazebo acceptance

The project is not fully accepted until one production-shaped run demonstrates:

- at least two namespaced AMRs moving independently in Gazebo/ROS 2;
- canonical telemetry reaching FastAPI and the browser 3D scene;
- a Backend task reaching Fleet/Task Manager and completing its lifecycle;
- an abnormal runtime condition producing a visible alert;
- an approved layout/scenario reaching the edge command service;
- `PENDING → ACKNOWLEDGED → COMPLETED` and the scenario changing to `APPLIED`
  only after success;
- timeout and explicit retry with the edge unavailable and restored;
- persistence/audit state surviving a Backend restart;
- measured ROS-to-Backend latency, Backend-to-browser latency and browser FPS.

Follow [`docs/runbooks/mvp-edge-acceptance.md`](runbooks/mvp-edge-acceptance.md)
and record results in the canonical acceptance record. CI is necessary but does
not replace this networked run.

## Evidence rules

- Evidence must name the commit and deployment IDs it represents.
- A screenshot must link to a test row and show only sanitized data.
- Latency/FPS claims require the sampling method, sample count, p50, p95 and max.
- Failed or missing observations remain `FAIL` or `PENDING`; do not infer PASS
  from source code or automated unit tests.
- Never commit credentials, tokens, edge secrets, database URLs or personal data.

## Current known model limits

- SimPy uses deterministic factory-flow assumptions rather than physical robot dynamics.
- The Gazebo navigation slice is deterministic and is not production-grade obstacle avoidance.
- Congestion is modeled and measured; collision is not yet an authoritative KPI.
- Incident replay UI, MES/ERP integration, AI/ML and long-term genealogy remain outside MVP.
