# Alert Management Controls

## Summary

Adds severity filtering, text search, ordering, and local acknowledgement controls to the shared
alert list used by the factory page and Overview alert popup.

## Motivation

An unfiltered read-only stream makes important incidents harder to find and repeatedly surfaces
alerts a user has already reviewed. The controls reduce local alert fatigue without changing the
authoritative runtime lifecycle.

## Architecture / Contract Impact

- Backend inspection found only `GET /api/v1/alerts`; neither an acknowledge endpoint nor an
  acknowledged field exists in the alert contract.
- Acknowledgement therefore stores alert IDs in Zustand only, separately from authoritative
  `ACTIVE` / `CLEARED` state. It is shared across mounted alert views and resets on logout/factory
  reset, but is intentionally not persisted across a page reload.
- A realtime clear removes the corresponding local acknowledgement. A fresh alert occurrence with
  a new ID remains visible.
- Filtering, search, limiting, and sorting are client-side presentation only. No frontend KPI,
  backend, WebSocket, simulation, or database contract changed.

## Files Changed

- `apps/frontend/src/components/alerts/alert-list.tsx`
- `apps/frontend/src/components/alerts/alert-list.test.tsx`
- `apps/frontend/src/stores/factory-store.ts`
- `apps/frontend/src/stores/factory-store.test.ts`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp8-alert-management.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/alerts/alert-list.test.tsx src/stores/factory-store.test.ts`: 2 files / 17 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 44 files / 209 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for severity filters, robot/task/message search, both sort modes, local
  acknowledgement, dismissed visibility, and shared state between factory and Overview views.

## CI / Build Impact

No dependency or CI configuration changed. Tests cover lifecycle preservation, severity and text
filters, local acknowledgement, dismissed visibility, and both sort modes.

## Follow-up

Add durable acknowledgement only as a separate backend contract checkpoint with actor and timestamp
provenance, authorization, persistence, and a WebSocket update shared by all clients.
