# Frontend–Backend Contract Convergence

## Summary

Aligned the frontend's advanced MVP contracts with the implemented FastAPI APIs. The
scenario workflow now includes submission, apply creates an asynchronous command,
and WebSocket command updates are retained in client state.

## Motivation

The frontend still implemented the earlier `SIMULATED → APPROVED → APPLIED` flow.
The authoritative Backend requires `SIMULATED → SUBMITTED → APPROVED`, accepts an
apply timeout/retry policy, and returns a command whose result is completed by the
edge Fleet Manager.

## Architecture / Contract Impact

- Added frontend Zod contracts for immutable layouts, optimization and commands.
- Expanded scenario configuration and metrics to the Backend's authoritative fields.
- Added `command.updated` to the shared realtime event handling path.
- Apply no longer treats command creation as immediate scenario application.
- Alert parsing now retains lifecycle, deduplication and operation metadata.

## Files Changed

- Frontend schemas, API client, realtime store and WebSocket event handling.
- Scenario submission/review/apply UI and scenario KPI comparison.
- Frontend unit and browser workflow tests.
- Frontend implementation guidance.

## Verification

Completed successfully:

- `npm run lint`
- `npm run typecheck`
- `npm test -- --run` — 26 files, 98 tests
- `npm run build` — Next.js production build
- `git diff --check`

## CI / Build Impact

The existing frontend CI commands remain unchanged. Hosted RBAC E2E now follows the
submitted lifecycle and stops at command creation because CI does not run an edge
Fleet Manager.

## Follow-up

- Connect the layout editor and optimization UI to the newly typed API methods.
- Add command history/retry UI and full ROS2 edge browser acceptance.
- Make the Backend robot registry authoritative for the configured edge fleet.
