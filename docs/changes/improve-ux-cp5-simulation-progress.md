# Simulation Progress Feedback

## Summary

Adds elapsed-time and indeterminate progress feedback while a scenario benchmark is running. Slow
runs produce one informational toast, and the UI states honestly that the current backend cannot
cancel a run in progress.

## Motivation

Changing only the submit-button label does not distinguish useful work from a stalled request.
Elapsed time and visible activity reassure the user without claiming server-side progress that the
current synchronous endpoint does not expose.

## Architecture / Contract Impact

- Separates form `busy` state from the actual `running` state so submit/review actions cannot show a
  false simulation timer.
- The elapsed timer is client-side wall time and is not an estimate of completed simulation work.
- A single informational toast appears after 60 seconds and all timers are cleaned up on completion,
  failure, or unmount.
- Repository inspection found no simulation cancel endpoint. The visible Cancel control is disabled
  and explicitly described as unavailable rather than pretending to cancel the request.
- No backend, REST, simulation, or database contract changed.

## Files Changed

- `apps/frontend/src/components/scenarios/scenario-run-form.tsx`
- `apps/frontend/src/components/scenarios/scenario-run-form.test.tsx`
- `apps/frontend/src/app/scenarios/page.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp5-simulation-progress.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/scenarios/scenario-run-form.test.tsx src/app/scenarios/page.test.tsx`: 2 files / 13 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 42 files / 196 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for elapsed timer, indeterminate progress, disabled cancellation guidance,
  and progress cleanup after completion.

## CI / Build Impact

No dependency or CI configuration changed. Vitest fake timers cover elapsed formatting, the
60-second warning, disabled cancellation, and cleanup after completion.

## Follow-up

If a server-side asynchronous simulation job contract is introduced later, replace indeterminate
feedback with authoritative progress and wire cancellation to that job endpoint.
