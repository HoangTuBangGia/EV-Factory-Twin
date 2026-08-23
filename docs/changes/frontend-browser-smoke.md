# Frontend Browser Smoke Flow

## Summary

Added an independent Playwright smoke suite for the fixture-backed Three.js factory
scene on desktop and mobile Chromium.

## Motivation

The existing browser suite requires backend and hosted Supabase credentials, so pull
requests without secrets had no real-browser coverage for the frontend 3D path.

## Architecture / Contract Impact

- The smoke suite starts only Next.js with `NEXT_PUBLIC_DATA_SOURCE=mock`.
- `/scene-probe` remains the deterministic visual fixture route.
- The probe uses viewport-relative dimensions so mobile browsers do not render a
  fixed 1440 px scene off-screen.
- Hosted Designer/Monitor E2E behavior and runtime contracts are unchanged.

## Files Changed

- `apps/frontend/playwright.smoke.config.ts`
- `apps/frontend/e2e/frontend-smoke/scene.spec.ts`
- `apps/frontend/package.json`
- `.github/workflows/ci.yml`
- `docs/development.md`

## Verification

- `npm test -- --run`: passed, 22 test files and 98 tests.
- `npm run lint`: passed after the final smoke/probe changes.
- `npm run typecheck`: passed after the final smoke/probe changes.
- `npm run test:smoke`: passed in desktop and mobile Chromium (2/2 tests).
- `npm run build`: passed and generated all 14 application routes.
- The first smoke run exposed the fixed-width mobile probe; after replacing the
  1440 px wrapper with viewport-relative sizing, both browser projects passed.

## CI / Build Impact

Frontend CI installs Chromium and runs `npm run test:smoke` without backend or hosted
credentials. This adds browser installation and two serial smoke projects to the job.

## Follow-up

Keep the hosted RBAC suite for authenticated cross-component workflow coverage.
