# WebSocket Offline Banner and Manual Reconnect

## Summary

Adds a persistent warning when live telemetry is disconnected and lets the operator immediately
request a clean reconnect. The banner reports reconnect progress and disappears for live or mock
data.

## Motivation

A small connection badge is insufficient when an operations view may be showing stale data. The
banner makes loss of live telemetry explicit and gives the operator a recovery control without
waiting for automatic backoff.

## Architecture / Contract Impact

- `FactorySocket` owns manual reconnect: it clears pending backoff/auth timers, detaches and closes
  the old transport, resets transient state, and opens one replacement transport.
- `useFactorySocket` exposes a stable reconnect callback for its currently owned socket.
- `DataProvider`, which owns the socket lifecycle, mounts the banner without placing callbacks in
  the factory Zustand data store.
- No backend, WebSocket message, REST, or database contract changed.

## Files Changed

- `apps/frontend/src/lib/websocket-client.ts`
- `apps/frontend/src/lib/websocket-client.test.ts`
- `apps/frontend/src/hooks/use-factory-socket.ts`
- `apps/frontend/src/hooks/use-factory-socket.test.ts`
- `apps/frontend/src/components/layout/connection-banner.tsx`
- `apps/frontend/src/components/layout/connection-banner.test.tsx`
- `apps/frontend/src/components/layout/data-provider.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp2-connection-banner.md`

## Verification

- Targeted Vitest: 3 files, 23 tests passed.
- Frontend ESLint: passed.
- TypeScript `tsc --noEmit`: passed.
- Full Vitest suite: 39 files, 182 tests passed.
- Next.js production build: passed; 14 static pages generated.
- Manual backend stop/restart smoke: passed; OFFLINE warning, manual CONNECTING state, restored
  LIVE status, and banner dismissal were confirmed.

## CI / Build Impact

No dependency or CI configuration changed. Existing frontend gates cover the socket, hook, UI,
types, and production build.

## Follow-up

Manually stop and restart a local backend to observe OFFLINE → CONNECTING → LIVE before closing
CP2. Start CP3 only after human review and commit.
