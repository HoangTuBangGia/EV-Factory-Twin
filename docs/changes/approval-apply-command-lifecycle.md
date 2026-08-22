# Approval and Apply Command Lifecycle

## Summary

Added scenario submission, durable apply commands, edge leasing, ROS execution,
acknowledgement, result, timeout/retry state and realtime command updates.

## Motivation

The previous apply endpoint reset MockFactory and marked a scenario APPLIED in
one request. It could not prove ROS acceptance or survive a Backend restart.

## Architecture / Contract Impact

- Scenario lifecycle now requires `SIMULATED → SUBMITTED → APPROVED/REJECTED`.
- Apply creates one durable operation with numbered attempts.
- Edge communication remains outbound-only and uses the existing shared secret.
- Fleet Manager caches results by operation/attempt for idempotent redelivery.
- Scenario becomes APPLIED only after a COMPLETED command result.
- Unsupported hot topology changes return FAILED and require Gazebo relaunch.

## Files Changed

Added command schemas/service/repositories/API, PostgreSQL migrations, ROS service,
edge polling/execution, lifecycle tests and canonical documentation updates. The
`SUBMITTED` enum addition is a separate migration so PostgreSQL commits it before
the command lifecycle migration uses the new value.

## Verification

- `make check`: Ruff, format-check and Mypy passed; 377 tests passed.
- `make ros-check` in `ros-jazzy`: 7 packages built; 43 tests passed.
- `make supabase-reset`: all migrations and seed applied successfully locally.
- `git diff --check`: passed.

## CI / Build Impact

Existing Python, integration and ROS gates cover the new code. No dependency was added.
The ROS developer command must run after sourcing `/opt/ros/jazzy/setup.bash`.

## Follow-up

Runtime health and telemetry retention are implemented by the M8 checkpoint.
