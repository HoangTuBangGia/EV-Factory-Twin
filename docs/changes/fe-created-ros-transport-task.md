# FE-created ROS Transport Task

## Summary

MONITOR can create a battery transport task in the Tasks UI. FastAPI persists a
typed durable command, the authenticated Telemetry Bridge leases it and calls
ROS `/fleet/tasks/create`, then command and task updates return to the UI.

## Motivation

The previous Tasks page was read-only and required a separate `ros2 service call`.
This left the required Browser → Backend → ROS direction unavailable to operators.

## Architecture / Contract Impact

The existing edge command channel now supports `APPLY_SCENARIO` and
`CREATE_TRANSPORT_TASK`. Migration `0016` backfills existing rows as apply
commands, makes `scenario_id` nullable only for task commands, and adds a task
target. Browser authentication and edge machine authentication remain separate;
the browser never accesses ROS DDS.

## Files Changed

- Backend task API, command schemas/service, and API tests.
- PostgreSQL command-contract migration and migration contract test.
- Telemetry Bridge task service dispatch and ROS unit test.
- Frontend task form, command rendering, schemas, client, and component tests.
- API and checkpoint documentation.

## Verification

Targeted Backend, Frontend, migration, and ROS checks are recorded in the
checkpoint handoff.

## CI / Build Impact

Python/Frontend CI validates both command variants. ROS CI builds the existing
`amr_interfaces` dependency and tests typed service dispatch. Environments must
apply migration `0016` before starting the updated Backend.

## Follow-up

Runtime scenario reconfiguration, collision events, and latency/render benchmarks
remain separate approved checkpoints. Task cancellation, priority, and direct
navigation are intentionally out of scope.
