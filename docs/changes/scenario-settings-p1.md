# Basic and Advanced Scenario Settings

## Summary

Split the Designer scenario form into an always-visible Basic section and a
collapsed Advanced section. Added layout-derived defaults, a live simulation
summary, and a reset action without changing the backend request contract.

## Motivation

The previous form presented every SimPy assumption at the same visual level.
Designers had to understand vehicle, charger, travel, and handling parameters
before they could run a routine layout benchmark.

## Architecture / Contract Impact

- `ScenarioRunRequest` and the REST API are unchanged.
- Layout, route, robot count, demand, task count, and duration remain in Basic.
- Speed, charger count, travel time, and loading time are disclosed as Advanced.
- Robot count, demand interval, speed, and charger count default from the selected layout.
- Advanced fields remain in the form while collapsed, so a Basic submission is complete.
- Existing backend/Zod validation remains authoritative at the page boundary.

## Files Changed

- Added `components/scenarios/scenario-run-form.tsx` and focused component tests.
- Replaced the inline form in `app/scenarios/page.tsx` with the new component.
- Added disclosure and summary styles in `app/globals.css`.
- Updated hosted RBAC E2E to open Advanced before editing advanced assumptions.
- Updated P1 progress in `docs/changes/fixUX.md`.

## Verification

Run from `apps/frontend`:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- Targeted `scenario-run-form.test.tsx`: 4 tests passed.
- `npm test -- --run`: 35 files and 158 tests passed on the confirmation run.
- `npm run test:e2e:list`: 3 tests discovered; hosted RBAC tests correctly skipped without credentials.
- `npm run build`: passed; all 14 static pages generated.

The first full-suite run had three unrelated five-second timeouts under parallel
load. Each affected file passed independently, and the unchanged full command
then passed completely; no timeout threshold or test behavior was weakened.

## CI / Build Impact

No dependency, API, backend, database, or workflow changes. One hosted E2E interaction
now opens the Advanced disclosure before filling travel and loading time.

## Follow-up

Optimization remains a separate advanced workflow and is addressed by P1 item 5.
