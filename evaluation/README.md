# EV Factory Twin Evaluation

`evaluation/` stores reproducible benchmark tooling and evidence for the current
Digital Twin acceptance boundary. It does not treat fixture-backed screenshots
or CI success as proof that the hosted ROS 2/Gazebo path works.

## Evaluation layers

1. **Automated quality gates** verify Python, database, frontend, browser smoke,
   ROS packages and containers independently.
2. **SimPy/layout evaluation** compares deterministic what-if candidates before
   human approval. The API workflow and immutable layout version are the
   authoritative product path; the standalone CSV evaluator remains a small
   reproducible fixture benchmark.
3. **Hosted edge acceptance** proves the complete networked path:

   ```text
   Layout → SimPy → Compare → Submit → Approve → Apply
                                               ↓
   Gazebo ↔ ROS 2 ↔ Edge bridge ↔ FastAPI ↔ WebSocket ↔ Browser
   ```

The current acceptance record is
[`reports/mvp-acceptance.md`](reports/mvp-acceptance.md). Keep it `PENDING` until
every mandatory observation has evidence from the same commit and deployment.

## Directory contract

| Path | Purpose | Commit policy |
|---|---|---|
| `benchmarks/` | Small benchmark definitions or metadata | Commit reviewed inputs only |
| `datasets/` | Generated standalone simulation output | Do not commit generated runs |
| `evidence/` | Screenshots/log extracts from the current acceptance run | Commit only sanitized, traceable evidence |
| `reports/` | Acceptance record and generated benchmark report | Never reuse observations from an older UI/runtime |
| `src/ev_evaluation/` | Reproducible CSV ranking utility | Covered by Python quality gates |
| `tests/` | Evaluator regression tests | Required when ranking changes |

Never commit credentials, access tokens, database URLs, edge secrets, personal
participant data or unredacted production logs.

## Standalone benchmark

From the repository root:

```bash
uv run --package ev-factory-simulation python -m ev_sim.batch
uv run --package ev-twin-evaluation python -m ev_evaluation.benchmark
```

The evaluator ranks completion rate and throughput first, then unfinished work,
cycle time and waiting time. This standalone pipeline is useful for deterministic
regression checks, but it does not replace the layout-aware API optimization or
the hosted edge acceptance run.

## Recording a new acceptance run

1. Copy/reset `reports/mvp-acceptance.md` for one commit and deployment set.
2. Follow `docs/runbooks/mvp-edge-acceptance.md` without skipping failure paths.
3. Store sanitized evidence under `evidence/` and link every claimed PASS.
4. Record actual values for all authoritative KPI, both latency boundaries and
   browser FPS.
5. Mark the overall decision PASS only when every mandatory row passes.
