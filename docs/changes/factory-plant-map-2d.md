# Factory Plant Blueprint Map

## Summary

The `/factory` route uses a detailed 120 × 40 metre SVG plant blueprint derived
from the procedural 3D factory. It includes view presets, pan and zoom, metric
measurement, SVG export, zone and equipment detail, and live AMR overlays.

## Motivation

The previous 2D fallback only showed the small configurable logistics layout.
Operators need a recognizable top-down view of the full EV plant while keeping
the existing realtime telemetry and layout controls.

## Architecture / Contract Impact

- The cloned prototype is not a runtime dependency.
- Plant geometry reuses `ev-factory-data.ts`, the same source as the 3D scene.
- AMRs, selected robot state, routes, stations, and no-go zones still use the
  existing Zustand and `FactoryLayout` contracts; prototype AMR simulation was removed.
- `FactoryMap` selects the plant blueprint through a 2D variant prop. The generic
  2D renderer remains available to the layout editor and WebGL fallback.
- No backend, REST, WebSocket, or telemetry contract changed.

## Files Changed

- `apps/frontend/src/components/factory/factory-plant-map-2d.tsx`
- `apps/frontend/src/components/factory/factory-map.tsx`
- `apps/frontend/src/components/factory/factory-map.test.tsx`
- `apps/frontend/src/app/factory/page.tsx`
- `apps/frontend/src/app/factory/page.test.tsx`
- `apps/frontend/src/app/globals.css`

## Verification

- `npm run lint` passed.
- `npm run typecheck` passed.
- Targeted Vitest suites passed: 3 files, 10 tests.
- `npm run test:smoke` passed on desktop and mobile Chromium: 2 tests.
- `npm run build` passed with 13 static pages generated.
- Human visual review of `/factory` remains pending.

## CI / Build Impact

No dependency or workflow changes are required. Existing frontend CI commands cover
the new component and route wiring.

## Follow-up

- Validate live-layout placement against the authoritative future 120 × 40 layout.
- Add equipment inspection only when a product contract exists for equipment state.
