# Toast Notification System

## Summary

Adds a lightweight, application-wide notification stack for user-triggered scenario and layout
actions. Success and informational messages expire after four seconds; errors remain until
dismissed.

## Motivation

Inline messages can be outside the user's viewport after a long scenario or layout interaction.
Toasts provide immediate feedback while the existing inline state remains available in context.

## Architecture / Contract Impact

- Adds a transient Zustand toast store with a maximum of three visible notifications.
- Mounts one toast container in the authenticated application frame.
- Does not change backend, API, database, or authoritative KPI contracts.
- Background loading and polling failures remain inline to avoid repeated notification noise.
- The current revision workflow uses `Request changes`; no obsolete reject action was added.

## Files Changed

- `apps/frontend/src/stores/toast-store.ts`
- `apps/frontend/src/components/ui/toast.tsx`
- `apps/frontend/src/components/ui/toast.test.tsx`
- `apps/frontend/src/components/layout/application-frame.tsx`
- `apps/frontend/src/app/scenarios/page.tsx`
- `apps/frontend/src/app/layouts/page.tsx`
- `apps/frontend/src/app/layouts/page.test.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp1-toast.md`

## Verification

- Targeted Vitest: 3 files, 19 tests passed.
- Frontend ESLint: passed.
- TypeScript `tsc --noEmit`: passed.
- Full Vitest suite: 38 files, 176 tests passed.
- Next.js production build: passed; 14 static pages generated.

## CI / Build Impact

No dependencies or CI configuration changed. Existing frontend lint, typecheck, Vitest, and
production build gates cover the implementation.

## Follow-up

Complete CP2 only after CP1 verification and human commit.
