# Styled Confirmation Dialog

## Summary

Replaces native browser confirmations for layout archival and scenario application with one
accessible, visually consistent confirmation dialog.

## Motivation

`window.confirm()` cannot present structured consequences, does not match the product interface,
and gives the application no control over focus behavior. Both affected actions can hide a layout
or reset live runtime state, so their confirmation should be explicit and consistent.

## Architecture / Contract Impact

- Adds a dependency-free `ConfirmDialog` UI component with a focus trap, Escape and overlay
  dismissal, body scroll locking, and focus restoration.
- Layout archival and scenario application remain unchanged after confirmation; no REST payload,
  authorization, backend, simulation, or database contract changed.
- Both actions use the danger treatment and describe their actual downstream consequences.
- Nested dialogs and forms inside the dialog remain unsupported by design.

## Files Changed

- `apps/frontend/src/components/ui/confirm-dialog.tsx`
- `apps/frontend/src/components/ui/confirm-dialog.test.tsx`
- `apps/frontend/src/app/layouts/page.tsx`
- `apps/frontend/src/app/layouts/page.test.tsx`
- `apps/frontend/src/app/scenarios/page.tsx`
- `apps/frontend/src/app/scenarios/page.test.tsx`
- `apps/frontend/e2e/hosted-rbac.spec.ts`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp6-confirm-dialog.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/ui/confirm-dialog.test.tsx src/app/layouts/page.test.tsx src/app/scenarios/page.test.tsx`: 3 files / 21 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 43 files / 201 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for layout archive and scenario apply confirmation, cancellation paths,
  keyboard focus containment, dismissal, and focus restoration.

## CI / Build Impact

No dependency or CI configuration changed. The hosted RBAC flow now confirms application through
the in-page accessible dialog instead of registering a native browser-dialog handler.

## Follow-up

Keep confirmation scoped to consequential actions. Routine edits and reversible view controls
should not gain confirmation dialogs.
