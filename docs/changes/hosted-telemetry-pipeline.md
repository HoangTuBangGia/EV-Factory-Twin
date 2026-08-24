# Hosted Telemetry Pipeline

## Summary

Decoupled realtime telemetry acknowledgement from cross-region PostgreSQL
history writes and reduced alert persistence to condition transitions.

## Motivation

Hosted acceptance measured bridge health at 1.98 seconds and a single telemetry
request timing out after 30 seconds. Each sample previously held the factory
lock while performing history and repeated alert transactions, so two 10 Hz AMRs
created an unbounded request backlog.

## Architecture / Contract Impact

- Accepted samples update state and broadcast before durable history I/O.
- A background latest-value buffer retains accepted and late samples separately
  per robot, flushes at a bounded configurable cadence and retries failures.
- Runtime alert persistence occurs only when a condition changes state.
- The source-ordering lock no longer covers network/database awaits.
- Edge HTTP operations allow five seconds for normal hosted network variance.
- API payloads, WebSocket events and database schema are unchanged.

## Files Changed

- Backend telemetry ingress, persistence lifecycle, health transitions and config.
- ROS bridge HTTP timeout and focused regression tests.
- Environment example and canonical API/architecture/deployment documentation.

## Verification

Run `make check`, PostgreSQL smoke and `make ros-check`. After merge/deploy, repeat
the isolated hosted timing probe before restarting the continuous bridge.

## CI / Build Impact

No dependency or migration is introduced. Existing Backend, PostgreSQL and ROS
quality gates cover the changed boundaries.

## Follow-up

Complete the hosted two-AMR telemetry, task, alert and apply-command acceptance
run and record latency/drop evidence without credentials.
