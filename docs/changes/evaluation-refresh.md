# Current MVP Evaluation Refresh

## Summary

Retired the fixture-backed August UI evidence and replaced it with a current,
traceable evaluation workspace, acceptance template and KPI documentation.

## Motivation

The previous report described the old mock UI and a reduced three-metric
benchmark. It could not substantiate the current immutable-layout workflow,
authoritative KPI set, durable apply command or hosted ROS 2/Gazebo boundary.

## Architecture / Contract Impact

- No runtime or API contract changes.
- Standalone CSV ranking now prefers completion rate before throughput and
  explicitly accounts for unfinished work.
- Hosted acceptance remains separate from standalone SimPy and CI evidence.

## Files Changed

- `evaluation/README.md`
- `evaluation/evidence/.gitkeep`
- `evaluation/reports/mvp-acceptance.md`
- `evaluation/src/ev_evaluation/benchmark.py`
- `evaluation/tests/test_benchmark.py`
- `docs/evaluation.md`
- Removed the obsolete `evaluation/reports/manual_eval_evidence.md` and eleven
  screenshots under `evaluation/evidence/`.

## Verification

- `uv run pytest evaluation/tests/test_benchmark.py`: 2 passed.
- `uv run ruff check evaluation`: passed.
- `uv run ruff format --check evaluation`: 5 files already formatted.
- `make typecheck`: passed for 89 source files.
- Hosted ROS 2/Gazebo acceptance remains `PENDING`; no result was inferred from
  source or automated checks.

## CI / Build Impact

The updated evaluator remains part of root Ruff, Mypy and Pytest gates. No new
dependency, service or generated artifact is introduced.

## Follow-up

Execute the hosted edge run and populate `evaluation/reports/mvp-acceptance.md`
with sanitized evidence from one reviewed commit/deployment set.
