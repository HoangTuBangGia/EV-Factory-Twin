# First-Login Onboarding Tour

## Summary

Adds a four-step, role-aware onboarding dialog for authenticated Designers and Monitors. Users can
complete or skip the tour, choose whether it returns, and navigate directly to their primary task.

## Motivation

Workflow guidance helps returning users decide what to do next, but it assumes familiarity with
the product and role model. The tour gives first-time users a concise explanation before they enter
the operational workflow.

## Architecture / Contract Impact

- Persistence uses `ft-onboarding-done:<user-id>` in browser local storage so two demo roles on one
  browser do not suppress each other's role-specific tour.
- The preference defaults to "Don't show again". Clearing it closes the tour only for the current
  mount, so it returns after reload.
- The custom modal traps focus, closes on Escape, restores prior focus, and locks background scroll.
- No backend, API, database, authorization, or navigation contract changed.

## Files Changed

- `apps/frontend/src/components/onboarding/onboarding-tour.tsx`
- `apps/frontend/src/components/onboarding/onboarding-tour.test.tsx`
- `apps/frontend/src/components/layout/application-frame.tsx`
- `apps/frontend/src/components/layout/application-frame.test.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp3-onboarding.md`

## Verification

- Targeted Vitest: 2 files, 5 tests passed.
- Frontend ESLint: passed.
- TypeScript `tsc --noEmit`: passed.
- Full Vitest suite: 40 files, 186 tests passed.
- Next.js production build: passed; 14 static pages generated.
- Manual Designer/Monitor desktop and mobile smoke: passed, including role destinations, keyboard
  containment, Escape, per-user persistence, and the non-persistent preference path.

## CI / Build Impact

No dependency or CI configuration changed. Vitest covers role content, persistence, navigation,
focus trapping, Escape, and focus restoration.

## Follow-up

Manually clear the per-user local-storage key and verify the tour on desktop and mobile for both
roles. Start CP4 only after human review and commit.
