# Frontend Fullscreen Operations Cockpit

## Summary

The Overview route is now a fullscreen 3D operations cockpit. Navigation opens
from a compact top-left menu, while statistics, fleet state, and recent alerts
open as mutually exclusive panels from a three-icon tool dock at the top right.

## Motivation

The previous dashboard constrained the Digital Twin inside a panel and divided
the viewport among cards, tables, and charts. Operations monitoring benefits
from keeping the factory scene as the primary surface and revealing supporting
information only when the operator requests it.

## Architecture / Contract Impact

- `/` uses a viewport-specific shell without the standard Topbar or content padding.
- Other routes retain their existing page layout and Topbar.
- Existing KPI, chart, fleet, alert, robot-detail, Zustand, REST, and WebSocket
  components remain the data boundaries; no backend contract changed.
- Navigation and tool panels support keyboard dismissal and accessible labels.
- The WebGL scene uses a demand-driven 30 FPS idle loop, reduced DPR, basic
  shadows, fewer point lights, cheaper transparent materials, and hidden roof
  trusses by default for lower-end GPUs.

## Files Changed

- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/components/dashboard/overview-tool-dock.tsx`
- `apps/frontend/src/components/dashboard/overview-tool-dock.test.tsx`
- `apps/frontend/src/components/layout/application-frame.tsx`
- `apps/frontend/src/components/layout/application-frame.test.tsx`
- `apps/frontend/src/components/layout/sidebar.tsx`
- `apps/frontend/src/components/layout/sidebar.test.tsx`
- `apps/frontend/src/components/factory/scene/factory-scene.tsx`
- `apps/frontend/src/components/factory/scene/ev-factory-map.ts`

## Verification

- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm test -- --run` passed: 25 test files, 89 tests.
- `npm run test:smoke` passed: desktop and mobile Chromium, 2 tests.
- `npm run build` passed with 13 static pages generated.
- Human visual and performance review on a representative low-end device remains pending.

## CI / Build Impact

No dependency or workflow changes are required. Existing frontend CI covers
the application shell, unit tests, browser WebGL smoke, and production build.

## Follow-up

- Capture FPS, frame-time, and dropped-frame evidence on the target weak machine.
- Tune the 30 FPS/DPR profile only from measured results.
- Consider a user-selectable quality profile if one fixed profile cannot cover
  both low-power laptops and high-resolution workstations.
