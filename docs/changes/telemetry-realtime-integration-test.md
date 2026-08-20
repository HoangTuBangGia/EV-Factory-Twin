# Telemetry Realtime Integration Test

## Summary

Added a cross-component integration test for edge telemetry delivery through REST,
WebSocket, and REST state.

## Motivation

Guard the complete backend telemetry path without replacing realtime broadcast
behavior.

## Architecture / Contract Impact

No production contract changes. The test exercises the real FastAPI lifespan,
telemetry route, authenticated factory WebSocket, and robot state route using the
same canonical fixture generated and asserted by the ROS bridge test.

## Files Changed

- `tests/integration/test_telemetry_realtime_flow.py`
- `docs/changes/telemetry-realtime-integration-test.md`

## Verification

`uv run pytest tests/integration/test_telemetry_realtime_flow.py` passed.

## CI / Build Impact

The existing root pytest configuration discovers the test; no dependency or CI
changes are required.

## Follow-up

None.
