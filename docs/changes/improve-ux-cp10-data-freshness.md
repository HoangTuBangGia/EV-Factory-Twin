# Data Freshness Indicator

## Summary

Adds one global timestamp for the latest applied factory data and displays its age in both the
standard topbar and full-screen Overview cockpit.

## Motivation

Connection state alone cannot reveal a silent or stalled live stream. Showing when displayed data
last changed lets an operator distinguish current state from a connected but stale view.

## Architecture / Contract Impact

- `lastUpdateAt` belongs to the frontend factory store and records when a complete REST snapshot or
  accepted realtime event is applied to the visible state.
- REST commits mark freshness once after all snapshot slices are installed. WebSocket and mock paths
  mark only after an event/tick is applied; paused buffered updates therefore do not make frozen data
  appear fresh.
- The indicator refreshes its relative label once per second. Only `LIVE` data older than 30 seconds
  raises `Data may be stale`, matching the requested operational threshold; `MOCK` still shows age.
- No per-entity timestamp, backend, REST, WebSocket, simulation, or database contract changed.

## Files Changed

- `apps/frontend/src/stores/factory-store.ts`
- `apps/frontend/src/stores/factory-store.test.ts`
- `apps/frontend/src/lib/factory-snapshot.ts`
- `apps/frontend/src/lib/factory-snapshot.test.ts`
- `apps/frontend/src/hooks/use-initial-factory-data.ts`
- `apps/frontend/src/hooks/use-factory-socket.ts`
- `apps/frontend/src/hooks/use-factory-socket.test.ts`
- `apps/frontend/src/hooks/use-mock-telemetry.ts`
- `apps/frontend/src/hooks/use-mock-telemetry.test.ts`
- `apps/frontend/src/components/layout/data-freshness-indicator.tsx`
- `apps/frontend/src/components/layout/data-freshness-indicator.test.tsx`
- `apps/frontend/src/components/layout/topbar.tsx`
- `apps/frontend/src/components/dashboard/overview-tool-dock.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp10-data-freshness.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/layout/data-freshness-indicator.test.tsx src/stores/factory-store.test.ts src/lib/factory-snapshot.test.ts src/hooks/use-factory-socket.test.ts src/hooks/use-mock-telemetry.test.ts src/components/dashboard/overview-tool-dock.test.tsx`: 6 files / 33 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 46 files / 217 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for MOCK and LIVE relative timestamps, pause/resume behavior, stale warning
  and recovery, and responsive placement in both Topbar and Overview cockpit.

## CI / Build Impact

No dependency or CI configuration changed. Tests cover formatting, the strict stale threshold,
store reset, REST commit, WebSocket pause/replay, mock pause/resume, and UI timer behavior.

## Follow-up

If the backend later exposes source timestamps, prefer that authoritative event time over browser
receipt time and document clock-skew handling.
