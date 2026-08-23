# M13 Authoritative ROS Robot Registry

## Summary

Removed mock robot seeding from ROS runtime mode and made the authenticated
telemetry bridge fleet list authoritative for Backend robot snapshots.

## Motivation

`MOCK_FACTORY_ENABLED=false` previously stopped the mock loop but still created
mock `AMR-01..N` records. That could expose ghost robots and reject a valid edge
fleet whose IDs differed from the mock defaults.

## Architecture / Contract Impact

- MOCK mode still seeds robots from `MOCK_ROBOT_COUNT`.
- ROS mode starts with an empty registry.
- Accepted, non-stale bridge health atomically replaces the current single-bridge
  robot ID set while preserving telemetry for unchanged IDs.
- New entries start OFFLINE until their first telemetry sample; removed entries
  disappear from snapshots.
- Registry changes emit `factory.reset` for REST rehydration.
- The bridge retains latest odometry and sends no telemetry until its initial
  health registration succeeds.
- ROS command completion marks the scenario APPLIED without resetting state via
  MockFactory; the edge Fleet Manager has already applied the command.

## Files Changed

- Backend factory state, edge health ingestion, runtime wiring and scenario apply.
- ROS telemetry bridge registration gate.
- Backend, ROS and cross-component regression tests.
- Architecture, development, deployment and requirement documentation.

## Verification

Run the targeted Backend/integration tests, then `make check` and `make ros-check`.
The hosted path is verified separately with
`docs/runbooks/mvp-edge-acceptance.md`.

## CI / Build Impact

Existing Backend and ROS workflows exercise the changed packages; no dependency,
migration or additional service is introduced.

## Follow-up

Run the hosted Render-to-GCP acceptance flow and record non-secret evidence. A
future multi-bridge deployment requires explicit bridge ownership and conflict
rules rather than reusing this single trusted bridge contract.
