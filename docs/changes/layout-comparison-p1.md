# Monitor layout comparison (P1 item 1)

## Summary

A Monitor reviewing a candidate can now see the geometry that candidate would put on
the floor, side by side with the geometry the factory runs today, plus a plain-language
list of what physically changed. The panel lives in the scenario review column on
`/scenarios`, collapsed by default, and only fetches geometry once it is opened.

The frontend permission table gains `layout:view` so read-only geometry inspection is
expressible for both roles; authoring geometry stays behind `layout:edit`.

## Motivation

`docs/changes/fixUX.md` P1 item 1: "Compare map current/candidate cho Monitor. Cần thêm
`layout:view` vào bảng permission frontend (C6); backend không đổi."

Before this change a Monitor approving a candidate saw only simulation metrics. The
layout revision the candidate was benchmarked on — the thing an apply actually pushes to
the floor — was invisible unless the Monitor navigated to the Designer-only editor, which
the frontend blocks. Approval was therefore a decision made without sight of its effect.

## Architecture / Contract Impact

- **No backend change.** Per C6 the Backend already lets both roles `GET` layout
  versions; only the frontend table was missing a name for that capability. `layout:view`
  is added to both DESIGNER and MONITOR, `layout:edit` stays Designer-only.
- **The "current" side is derived, not stored** (C1). `latestAppliedScenario` gives the
  newest APPLIED scenario; its `config.layout_id + layout_version` identifies the live
  geometry. When no candidate has been applied yet the panel says so instead of inventing
  a baseline, and when the candidate targets the same revision it says the geometry is
  unchanged and loads it once.
- **The diff is a pure function.** `lib/layout-diff.ts` exports
  `diffLayoutContent(current, candidate): LayoutChange[]` over `LayoutVersionContent`,
  with no React or network dependency, so it is unit-testable in isolation. It reports
  footprint, station add/move/remove (move as a metre distance), route
  add/reroute/endpoint-change/remove, no-go and congestion zone reshape/delay changes, and
  the four runtime config fields.
- **Fetch is lazy.** The panel is a `<details>`; the `useEffect` returns early unless it
  is open, so an unexpanded review costs no request. Both revisions load in one
  `Promise.all`, and a rejection degrades to an inline notice rather than breaking review.
- **Rendering reuses `FactoryPlantMap2D`** via `projectLayoutVersion`, with all layers on.
  No new map component.
- **No new DOM contracts broken** (C10): the panel adds no `role="status"`, no
  `.scenario-status`, and nothing inside `.scenario-tabs`, so the hosted RBAC e2e
  count assertions still hold.
- Styling is one additional compressed line in `globals.css` following the existing
  hand-rolled convention (C9); no design system introduced.

## Files Changed

| File | Change |
| --- | --- |
| `apps/frontend/src/lib/auth/permissions.ts` | Added `layout:view` to the permission union and to both role lists, with a comment on why both roles hold it. |
| `apps/frontend/src/lib/auth/permissions.test.ts` | New test asserting both roles read geometry and only Designer authors it. |
| `apps/frontend/src/lib/layout-diff.ts` | **New.** Pure `diffLayoutContent` + `LayoutChange`. |
| `apps/frontend/src/lib/layout-diff.test.ts` | **New.** 6 tests over the diff's exact wording. |
| `apps/frontend/src/components/scenarios/layout-comparison.tsx` | **New.** Collapsible current/candidate maps + change list. |
| `apps/frontend/src/components/scenarios/layout-comparison.test.tsx` | **New.** 5 tests: lazy fetch, both revisions rendered, unchanged-geometry case, no-baseline case, fetch failure. |
| `apps/frontend/src/app/scenarios/page.tsx` | Renders `LayoutComparison` in the review column behind `can(user.role, "layout:view")`. |
| `apps/frontend/src/lib/fixtures.ts` | Added `fixtureLayoutVersion` shared by both new test files. |
| `apps/frontend/src/app/globals.css` | One line: `.layout-comparison`, its maps grid and change list. |
| `apps/frontend/src/app/layouts/page.tsx` | Carried over from the P0 follow-up: `VersionCandidate` wires `candidateForLayoutVersion` into the editor. |
| `apps/frontend/src/app/layouts/page.test.tsx` | Two tests for that wiring; shared `savedLayout` mock helper. |
| `docs/changes/fixUX.md` | Progress section records P1 item 1 as done. |
| `docs/changes/workflow-guidance-p0.md` | Architecture/verification amended after the editor wiring. |

## Verification

Run from `apps/frontend`:

- `npm run lint` — clean.
- `npm run typecheck` — clean.
- `npm test -- --run` — 34 files, 151 tests pass (up from 32 / 139).
- `npm run build` — succeeds, 14/14 pages generated.

`npm run test:e2e` was not run; it self-skips without a hosted stack, and the DOM
selectors it asserts on were deliberately left untouched.

## CI / Build Impact

No new dependencies, no config changes. Route JS for `/scenarios` grows from the added
component; `/layouts` and shared chunks are unchanged in kind. Two new test files add
~0.25 s to the suite.

## Follow-up

- P1 items 2–5 remain unstarted.
- The congestion story is still one aggregate number (C5); the change list can say a zone
  was reshaped but cannot attribute delay to it.
- `use-applied-factory-layout.ts` still issues its own `GET /scenarios` alongside the
  store; the comparison panel reads the store and does not add a third fetch, but the
  existing duplication is untouched.
