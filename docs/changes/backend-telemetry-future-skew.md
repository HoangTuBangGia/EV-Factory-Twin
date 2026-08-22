# Backend Telemetry Future-Skew Validation

## Summary

The authenticated backend telemetry ingress now rejects source timestamps more
than a configurable number of seconds ahead of backend UTC.

## Motivation

An accepted far-future sample could poison `last_seen_at` and cause subsequent
valid telemetry to be treated as stale.

## Architecture / Contract Impact

Validation remains at the backend trust boundary. The canonical telemetry and
WebSocket contracts are unchanged. Over-limit samples return HTTP 422 without
changing state or broadcasting; stale and duplicate samples remain idempotent.
`EDGE_TELEMETRY_MAX_FUTURE_SKEW_SECONDS` defaults to 5 and accepts 0–300.

## Files Changed

Updated backend settings, ingress service wiring, HTTP error mapping, regression
tests, environment example, and telemetry documentation. No ROS files changed.

## Verification

Passed targeted ingress/config tests, the full Python suite as part of `make check`,
migration checks, repository-wide Ruff/format checks, and Mypy.

## CI / Build Impact

No dependencies or workflow changes. Existing Python CI covers the behavior.

## Follow-up

None for the current single-bridge scope.
