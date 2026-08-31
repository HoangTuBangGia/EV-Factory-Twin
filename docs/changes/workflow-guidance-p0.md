# Workflow Guidance P0

## Summary

Made the candidate review workflow legible in the UI without touching the API
contract: a role-aware "Next step" strip in the application frame, a stage +
apply-phase timeline on each candidate, derived review queues on `/scenarios`,
and a route-drawing stepper plus revision wording on `/layouts`.

## Motivation

The UX audit in `docs/changes/fixUX.md` found that both roles had to infer the
workflow from status badges. A Designer could not tell that a `SIMULATED`
candidate is invisible to Monitors until submitted, a Monitor had no inbox for
`SUBMITTED` work, and the two-phase apply (command queued now, runtime changed
when the bridge completes) was rendered as a single instant action. Route
drawing gave no indication of which click came next.

## Architecture / Contract Impact

- `lib/workflow.ts` holds every derivation as pure functions: stage state from
  `ScenarioStatus`, apply phase from `Command.attempts`, queue filters, and the
  per-role next action. No endpoint, schema or migration changed.
- A "candidate" stays a frontend-derived view model. `candidateForLayoutVersion` joins
  `scenario.config.layout_id + layout_version` and picks the newest match, because a layout
  version carries no workflow status of its own. The Layouts editor uses it to report where the
  open revision sits in review; it reads `scenarios` from the store rather than fetching again.
- `REJECTED` is modelled as a terminal failed review, not a fifth stage, and the
  copy states that a rejected candidate cannot be resubmitted.
- Apply progress reads `acknowledged_at` from the attempts rather than the
  command status, so a command that later failed still shows how far it got, and
  the failure hint says the factory runtime is unchanged.
- `scenarios` moved into the factory store so the frame-level strip and the
  Scenarios page share one list; the page's local upsert helper was removed.
- Queue chips are URL-driven (`/scenarios?queue=awaiting`) so the strip can link
  straight into a filtered queue. The default queue stays `all`.
- The timeline renders a candidate's command only when `command.scenario_id`
  matches, so a previously applied candidate's phases cannot leak onto another.
- New UI deliberately avoids `role="status"` and `.scenario-status`, which the
  hosted RBAC e2e spec asserts as single elements. Existing button labels and
  notice strings that tests assert are unchanged.

## Files Changed

- New `apps/frontend/src/lib/workflow.ts` and its unit test.
- New `apps/frontend/src/components/workflow/` — timeline, next-action strip and
  their component test.
- Frontend store (`scenarios`, `setScenarios`, `updateScenario`), application
  frame and its test, Scenarios page, Layouts page and its test, global
  stylesheet, shared test fixtures (`fixtureScenario`, `fixtureApplyCommand`).

## Verification

Run from `apps/frontend`: `npm run lint` (clean), `npm run typecheck` (clean),
`npm test` (32 files / 139 tests pass), `npm run build` (14/14 pages).
`npm run test:e2e` self-skips without hosted RBAC credentials
(`DESIGNER_EMAIL`, `MONITOR_EMAIL`), so it must be confirmed in CI.

## CI / Build Impact

No new dependency, service or environment variable. Existing frontend quality
gates cover the new module and components.

## Follow-up

- The strip and the Scenarios page each issue `GET /scenarios`, alongside the
  existing duplicate fetch in `hooks/use-applied-factory-layout.ts`. Collapsing
  these into one hydration path is a separate checkpoint.
- P1 and P2 items from the audit (baseline comparison, zone-level congestion
  attribution, design-system consolidation) remain out of scope; zone
  attribution additionally needs a backend metric that does not exist yet.
