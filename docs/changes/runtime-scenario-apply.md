# Runtime Scenario Apply

## Summary

Scenario Apply now distinguishes live-compatible speed updates from ROS/Gazebo
configuration changes that require a relaunch.

## Motivation

The previous Fleet Manager accepted only an already-identical configuration and
did not change robot runtime behavior. Backend could therefore mark a scenario
APPLIED without a real ROS update.

## Architecture / Contract Impact

- Navigation simulators expose a typed speed-update service.
- Fleet Manager applies speed to every configured robot and completes only after
  every service confirms success.
- Robot count, charger count, layout, route and demand interval differences return
  `REQUIRES_RELAUNCH`; demand remains a declared runtime input because no live ROS
  component currently generates periodic demand.
- Bridge heartbeat includes the declared live runtime configuration. Backend uses
  it for `GET /api/v1/scenarios/{id}/compatibility`.
- Only `COMPLETED` moves an approved scenario to `APPLIED`.

## Files Changed

Backend command/runtime schemas and services, PostgreSQL migration 0017, ROS
interfaces/nodes/launch files, frontend scenario/command views, tests and docs.

## Verification

Pending human-run Backend, Frontend, ROS and migration checks.

## CI / Build Impact

ROS interface generation must run before ROS package tests. PostgreSQL migration
0017 must be applied before the updated Backend accepts the new enum value.

## Follow-up

No demand generator is added. A future explicitly approved feature would need to
define demand ownership before `demand_interval_seconds` can become live-mutable.
