# Pause and Resume Live Updates

## Summary

Adds a global pause control to the standard topbar and Overview cockpit. API-mode telemetry is
buffered while the view is paused, and fixture animation freezes until the operator resumes.

## Motivation

Operators need to inspect a pose, KPI, task, or alert without the view changing underneath them.
Pause is a presentation control only: the live connection remains active and data catches up on
resume.

## Architecture / Contract Impact

- Zustand owns the transient `paused` flag; logout/reset and refresh restore normal live updates.
- The WebSocket hook buffers at most 500 ordered events and defers reconnect snapshots. Resume
  commits the deferred snapshot first and then replays later events.
- On overflow, the oldest event is discarded and one informational warning is shown per pause;
  resume refetches an authoritative snapshot instead of replaying an incomplete event sequence.
- Disconnect clears stale buffered state; a reconnect snapshot becomes the new resume baseline.
- Mock telemetry skips animation ticks while paused because fixture ticks are generated locally and
  do not represent authoritative events that need catch-up.
- No backend, REST, WebSocket message, or database contract changed.

## Files Changed

- `apps/frontend/src/stores/factory-store.ts`
- `apps/frontend/src/stores/factory-store.test.ts`
- `apps/frontend/src/hooks/use-factory-socket.ts`
- `apps/frontend/src/hooks/use-factory-socket.test.ts`
- `apps/frontend/src/hooks/use-mock-telemetry.ts`
- `apps/frontend/src/hooks/use-mock-telemetry.test.ts`
- `apps/frontend/src/components/layout/live-pause-button.tsx`
- `apps/frontend/src/components/layout/live-pause-button.test.tsx`
- `apps/frontend/src/components/layout/topbar.tsx`
- `apps/frontend/src/components/dashboard/overview-tool-dock.tsx`
- `apps/frontend/src/components/dashboard/overview-tool-dock.test.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp4-pause-live-updates.md`

## Verification

- Targeted Vitest: 5 files, 27 tests passed.
- Frontend ESLint: passed.
- TypeScript `tsc --noEmit`: passed.
- Full Vitest suite: 42 files, 193 tests passed.
- Next.js production build: passed; 14 static pages generated.
- Manual MOCK/API smoke: passed, including frozen views, catch-up on resume, reconnect while paused,
  synchronized topbar/cockpit controls, and reset to live updates after reload/logout.

## CI / Build Impact

No dependency or CI configuration changed. Unit tests cover state reset, API event buffering,
snapshot deferral, overflow warning, mock animation, and both control presentations.

## Follow-up

Manually pause and resume both API and fixture modes before closing CP4. Start CP5 only after human
review and commit.
