# Authenticated Edge Telemetry Ingress

## Summary

Added a machine-authenticated FastAPI endpoint that accepts canonical
`RobotTelemetry`, updates runtime robot state, and broadcasts the existing
`robot.telemetry` browser event.

## Motivation

ROS/Gazebo telemetry needs a secure application boundary before the first edge
bridge and robotics vertical slice can be implemented.

## Architecture / Contract Impact

- `POST /internal/v1/telemetry` uses an independent opaque bearer secret.
- Supabase user JWTs and service-role keys are not accepted as edge identity.
- Samples older than or equal to current robot state are idempotent no-ops.
- Unknown robots are rejected; the edge cannot create registry entries.
- Mock and edge sources cannot write concurrently.
- The current trust model is one trusted bridge and one backend instance; the
  shared secret is fleet-wide and does not provide per-robot attribution.
- Accepted samples use the same twin-core contract and `/ws/factory` event as MOCK.

## Files Changed

Added the edge route and ingress service; updated settings, application wiring,
telemetry response schemas, environment examples, tests, and canonical docs.

## Verification

Passed: targeted ingress/WebSocket tests, `make check` (`388 passed`), migration
checks, frontend lint/typecheck/unit tests, and the production frontend build.

## CI / Build Impact

No new dependency or workflow is required. Existing Python CI covers the route,
service, configuration, and contract tests.

## Follow-up

Implement the ROS 2 `telemetry_bridge` client, use a managed secret at the edge,
and add a Gazebo-to-browser integration gate. Batch ingestion, request-size
limiting, overlapping secret rotation, per-bridge identity, multi-instance pub/sub,
and durable telemetry history remain separate measured requirements.
