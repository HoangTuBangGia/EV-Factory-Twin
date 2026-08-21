# Multi-Robot Telemetry Bridge

## Summary

Added one fleet-configured ROS 2 bridge for multi-robot telemetry, task updates
and bridge-health heartbeats into the unified FastAPI runtime contract.

## Motivation

The earlier bridge handled one namespaced robot per process and did not forward
task/payload state or Fleet Manager execution transitions.

## Architecture / Contract Impact

- One bridge loads the validated robot JSON and subscribes to each namespace.
- Each robot has an independent latest-value telemetry worker and stale ordering.
- Task transitions retain FIFO ordering and become Backend `task.updated` events.
- Bridge health reports delivery counters and outstanding errors per robot.
- All machine endpoints share the edge bearer secret; browser auth remains JWT.

## Files Changed

Updated the ROS telemetry bridge, launch and Gazebo integration test; added the
FastAPI edge runtime schemas/router/service and their unit/integration tests;
updated canonical runtime, API, development and deployment documentation.

## Verification

Backend unit/API/integration tests cover independent robot ordering, task
snapshot/WebSocket fan-out, stale task updates and latest bridge health. ROS
tests cover fleet configuration, task FIFO delivery and the two-AMR Gazebo path.

## CI / Build Impact

The existing Python and ROS gates exercise the new code. The bridge now depends
on the existing `amr_interfaces` ROS package; no third-party dependency was added.

## Follow-up

Persist bridge health and telemetry history, generate disconnect/stale alerts,
and add the authenticated command/acknowledgement path during approval/apply.
