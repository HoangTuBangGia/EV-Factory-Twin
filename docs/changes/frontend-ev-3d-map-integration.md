# Frontend EV 3D Map Integration

## Summary

The Factory monitor now uses the procedural 120 × 40 metre EV production plant
from `EV-3D-map` as its primary WebGL environment. Canonical realtime AMRs,
selection, robot details, layout overlays, layer controls, and the 2D fallback
remain owned by the existing frontend application.

## Motivation

The previous WebGL environment represented only a small battery-transfer room
and did not visually read as an EV factory. The imported scene adds receiving,
storage, casting, robotic welding, assembly, quality-control, finished-goods,
and shipping areas without introducing external model files or dependencies.

## Architecture / Contract Impact

- No REST, WebSocket, telemetry, layout, or KPI contract changed.
- The imported prototype AMRs are disabled by default. Only robots from the
  canonical Zustand telemetry store are rendered on the operational screen.
- The current 20 × 15 metre data-driven layout is retained as the live overlay
  at the centre of the larger factory environment.
- WebGL detection and the existing data-driven 2D fallback are unchanged.

## Files Changed

- `apps/frontend/src/components/factory/factory-map.tsx`
- `apps/frontend/src/app/factory/page.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/components/factory/scene/factory-scene.tsx`
- `apps/frontend/src/components/factory/scene/ev-factory-constants.ts`
- `apps/frontend/src/components/factory/scene/ev-factory-data.ts`
- `apps/frontend/src/components/factory/scene/ev-factory-environment.tsx`
- `apps/frontend/src/components/factory/scene/ev-factory-map.ts`
- `apps/frontend/src/components/factory/scene/ev-factory-map.test.ts`
- `.gitignore`

## Verification

- `npm run lint`: passed.
- `npm run typecheck`: passed after the production build regenerated stale
  `.next/types` route metadata.
- `npm test -- --run`: passed, 22 test files and 86 tests.
- `npm run test:smoke`: passed in desktop and mobile Chromium; the fixture-backed
  WebGL scene rendered without browser or page errors.
- `npm run build`: passed with all 13 application pages generated.
- Detailed human visual review of camera composition remains a follow-up.

## CI / Build Impact

No dependency or workflow change is required. Existing frontend CI commands
cover lint, types, unit tests, Playwright smoke, and the Next.js production build.
The procedural geometry increases the client-side 3D scene size and should be
included in the planned FPS/render benchmark.

## Follow-up

- Visually tune the live 20 × 15 metre overlay after browser inspection.
- Connect the full factory footprint to the future versioned layout contract.
- Record FPS and dropped-frame evidence with representative AMR counts.
