# Full Factory Layout Workflow

## Summary

Aligned the 120 × 40 m EV factory map, versioned layout editor, SimPy route
profile, mock factory movement, and applied 2D/3D visualization around one
immutable layout version.

## Motivation

The detailed plant map previously displayed a legacy 20 × 15 m operational
overlay. Moving stations or saving a route changed frontend geometry but did not
change mock-runtime movement, so layout experiments were not end to end.

## Architecture / Contract Impact

- `LAYOUT-DEFAULT` version 2 is the canonical 120 × 40 m fallback; version 1 is
  preserved because layout versions are append-only.
- Layout coordinates remain `(x, y)` in factory metres. The renderer maps them
  to plant `(x, z)` without changing the API contract.
- SimPy derives route distance and congestion from the selected layout version.
- Approved scenario apply now projects layout geometry and route into the mock
  runtime before reset. Failed apply restores both previous config and layout.
- Designer editing remains separate from Monitor approval: save layout → run
  scenario → submit → approve → apply.

## Files Changed

- Added the canonical layout to `twin-core` and ledger-backed PostgreSQL
  migrations.
- Replaced backend fixed station/route tables with active-layout projections.
- Added station dragging and route drawing to the `/factory` 2D workspace.
- Removed the legacy design-route and live-layout overlays from the plant map.
- Made overview 3D and factory 2D reload the same applied layout.
- Added backend, SimPy, twin-core, and frontend regression coverage.

## Verification

- `make check`: passed Ruff lint, Ruff format check, mypy, and 409 pytest tests;
  2 PostgreSQL smoke tests were skipped because `TEST_DATABASE_URL` was not set.
- `make frontend-check`: passed ESLint, TypeScript, 108 Vitest tests, and the
  Next.js 15.5.23 production build.

## CI / Build Impact

No dependency or workflow changes. Existing Python and frontend gates cover the
new contract and UI behavior. Cloud SQL must apply migration `0011` before using
default layout version 2.

## Follow-up

- Gazebo/Nav2 still needs a topology-aware adapter before arbitrary route
  geometry can be applied to physical/ROS runtime; unsupported edge changes
  continue through the existing command failure path.
- Direct polygon editing for no-go and congestion zones remains JSON-based in
  this MVP checkpoint.
