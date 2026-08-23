# M11 Layout and Planning UI

## Summary

Connected the frontend layout, scenario, optimization and runtime-map workflows
to the existing Backend contracts.

## Motivation

The previous layout screen was a local draft and scenario inputs silently used
default layout values. The MVP requires immutable layout provenance from design
through simulation, approval, apply and monitoring.

## Architecture / Contract Impact

- Layout CRUD and immutable version creation use `/api/v1/layouts`.
- Scenario runs send an explicit layout version and route plus fleet, demand,
  speed and charger inputs.
- Optimization uses the deterministic Backend endpoint and keeps its 64-candidate bound.
- The factory map projects the latest APPLIED scenario's immutable layout into
  the existing rendering contract, refreshes it after `factory.reset`, and uses
  the versioned default as fallback.
- No new Backend endpoint or database migration was introduced.

## Files Changed

- Frontend layout editor, scenario sandbox, optimizer and factory map.
- Shared frontend layout projection and focused tests.
- Root Makefile frontend workflows.
- Canonical API, requirements, team and development documentation.

## Verification

Run `make frontend-check` after installing locked frontend dependencies with
`make frontend-sync`. Run `make check` for the unchanged Backend contracts.

## CI / Build Impact

CI can call the same Makefile targets used locally. The frontend production
build remains part of `frontend-check`.

## Follow-up

M12 adds command history, attempts and retry UI. M13 removes mock robot registry
assumptions from ROS runtime mode before final ROS acceptance.
