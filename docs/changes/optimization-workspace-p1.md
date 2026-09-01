# Advanced Optimization Workspace

## Summary

Reframed bounded flow optimization as a collapsed advanced workflow on the
Scenarios page. Added a live Cartesian candidate count, pre-submit limit
feedback, and a deep link to the recommended scenario.

## Motivation

The previous always-expanded panel looked like a second primary scenario form
and sat without a clear place in the product journey. Optimization evaluates
multiple immutable layouts and operating assumptions, so it belongs beside
scenario simulation as an optional Designer tool rather than in geometry editing.

## Architecture / Contract Impact

- The existing deterministic `POST /optimizations/run` contract is unchanged.
- UI and Zod validation share one Cartesian candidate-count helper.
- The 64-candidate backend limit is shown before submission and disables the action.
- Optimization remains Designer-only through the existing `scenarios:run` permission.
- Recommendation links use `/scenarios?candidate=<id>`; Scenarios selects that
  durable candidate after loading history.
- No optimization result is automatically reviewed, approved, or applied.

## Files Changed

- Updated `OptimizationPanel` placement, disclosure, count feedback, and result link.
- Added shared candidate counting and schema tests.
- Added recommendation query selection and page regression coverage.
- Added advanced-workspace styling and updated `docs/changes/fixUX.md`.

## Verification

Run from `apps/frontend`:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- Focused schema/panel/Scenarios tests: 3 files and 8 tests passed.
- `npm test -- --run`: 37 files and 166 tests passed.
- `npm run test:e2e:list`: 3 tests discovered; hosted RBAC tests correctly skipped without credentials.
- `npm run build`: passed; all 14 static pages generated.

## CI / Build Impact

No dependency, backend, database, API contract, or CI workflow changes.

## Follow-up

Comma-separated dimension inputs remain intentionally simple. Replacing them
with a chip editor is not required for the bounded MVP workflow.
