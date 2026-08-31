# Breadcrumb Navigation

## Summary

Replaces the static application title in the standard topbar with route-derived breadcrumbs and
centralizes primary navigation metadata for reuse by the sidebar.

## Motivation

The static product title does not tell users which workspace or selected candidate they are viewing.
A concise trail improves orientation and gives deep query routes a direct link back to their parent.

## Architecture / Contract Impact

- Adds pure pathname/query parsing in `lib/navigation.ts`; breadcrumbs remain route-based and do not
  track browser history.
- Sidebar and breadcrumbs now share the same canonical primary route labels.
- Candidate and layout query values are displayed as text only. URL encoding is handled by
  `URLSearchParams`, and the final breadcrumb is never rendered as a link.
- `/layouts?id=...` affects breadcrumb orientation only; CP9 does not add query-driven layout
  selection behavior.
- Mobile CSS hides intermediate levels beyond three while retaining the first and final two levels.
- No authorization, backend, API, simulation, WebSocket, or database contract changed.

## Files Changed

- `apps/frontend/src/lib/navigation.ts`
- `apps/frontend/src/components/layout/breadcrumbs.tsx`
- `apps/frontend/src/components/layout/breadcrumbs.test.tsx`
- `apps/frontend/src/components/layout/sidebar.tsx`
- `apps/frontend/src/components/layout/topbar.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp9-breadcrumbs.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/layout/breadcrumbs.test.tsx src/components/layout/sidebar.test.tsx src/components/layout/application-frame.test.tsx`: 3 files / 5 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 45 files / 212 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for primary routes, scenario/layout query trails, parent navigation,
  responsive truncation, and unchanged role-filtered sidebar behavior.

## CI / Build Impact

No dependency or CI configuration changed. The breadcrumb query reader is isolated behind React
Suspense so static page generation keeps a deterministic fallback.

## Follow-up

If Layouts later supports URL-addressable selection, reuse the existing `id` query rather than
introducing a second route convention.
