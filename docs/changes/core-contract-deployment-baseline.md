# CORE Contract and Deployment Baseline

## Summary

Moved the source-neutral robot telemetry contract into `twin-core`, fixed the
canonical browser WebSocket path, and recorded the cloud/edge deployment decision.

## Motivation

MOCK, ROS, and REPLAY need one telemetry contract before ROS ingress and replay
are implemented. Empty deployment and CI placeholders also overstated repository
readiness.

## Architecture / Contract Impact

- `twin-core` now owns `RobotStatus`, `Pose`, `Velocity`, and `RobotTelemetry`.
- Existing backend imports and serialized payloads remain compatible.
- `/ws/factory` is canonical for browsers.
- Edge robotics runs outside the cloud and will use a separate authenticated
  ingress boundary.
- Supabase PostgreSQL 17 is the database baseline; TimescaleDB is not assumed.

## Files Changed

Updated twin-core/backend telemetry modules, CORE requirements, architecture,
deployment ADRs, and removed empty Docker/Compose/workflow placeholders.

## Verification

Passed: `uv sync --locked --all-packages --dev`, `uv lock --check`, 16 targeted
telemetry/schema tests, 374 full Python tests, Ruff, format check, mypy, frontend lint/typecheck, 94
frontend unit tests, and `next build`. The reproducible Makefile command passed
after isolating unrelated ROS pytest
plugins and clearing the local database URL. Direct plain `uv run pytest` remains
environment-sensitive when ROS plugins or a developer `.env` are globally active.

## CI / Build Impact

The existing Python/frontend CI remains authoritative. ROS, Docker, and deploy
workflows will be added with the first real buildable artifact, not as empty files.

## Follow-up

Implement authenticated edge ingress and the first Gazebo-to-browser vertical
slice, then add its ROS and integration CI gates in the same checkpoint.
