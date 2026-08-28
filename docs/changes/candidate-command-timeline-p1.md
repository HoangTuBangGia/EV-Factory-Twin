# Candidate Command Timeline

## Summary

Integrated durable factory-apply commands into the candidate workflow timeline.
The Scenarios page now restores command state after reload, follows live
WebSocket updates through Zustand, and links to the Commands diagnostic page.

## Motivation

Previously the Scenarios page kept only the operation ID returned by the current
Apply click. Reloading lost that local ID, so an existing PENDING,
ACKNOWLEDGED, COMPLETED, or failed command disappeared from the candidate even
though Backend still retained it.

## Architecture / Contract Impact

- Existing `GET /commands`, command schema, and WebSocket events are reused.
- Scenarios hydrates command history once during page load.
- A pure selector resolves the most recently updated command for each scenario,
  including a later retry operation.
- Failed command-history hydration is supplemental and does not block scenario,
  layout, baseline, or KPI loading.
- Commands remains the diagnostic and retry workspace; Scenarios presents the
  user-facing lifecycle and links to technical details.

## Files Changed

- Added durable command selection to `lib/workflow.ts` with unit coverage.
- Extended `WorkflowTimeline` with status, timestamps, bridge detail, and diagnostic link.
- Updated `app/scenarios/page.tsx` to hydrate and derive command state from Zustand.
- Added Scenarios page hydration/failure regression tests and timeline styling.
- Updated P1 progress in `docs/changes/fixUX.md`.

## Verification

Run from `apps/frontend`:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- Focused workflow/timeline/Scenarios tests: 3 files and 30 tests passed.
- `npm test -- --run`: 36 files and 161 tests passed.
- `npm run test:e2e:list`: 3 tests discovered; hosted RBAC tests correctly skipped without credentials.
- `npm run build`: passed; all 14 static pages generated.

## CI / Build Impact

No dependency, backend, database, contract, or workflow changes.

## Follow-up

The existing Commands page still owns retry actions and detailed attempt tables.
Consolidating all frontend hydration paths is a separate fetch-deduplication checkpoint.
