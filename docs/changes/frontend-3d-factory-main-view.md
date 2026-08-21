# Frontend 3D Factory Main View

## Summary

The factory page now prefers the existing Three.js scene, retains the 2D WebGL
fallback, and provides working controls for station, route, and no-go layers.

## Motivation

The production factory route forced the 2D renderer even though the MVP agreement
requires the 3D scene to be the primary monitoring surface.

## Architecture / Contract Impact

No backend or realtime contract changed. Layer visibility is local presentation
state and is applied consistently to the 3D scene and its 2D fallback.

## Files Changed

- `apps/frontend/src/app/factory/page.tsx`
- `apps/frontend/src/app/factory/page.test.tsx`
- `apps/frontend/src/components/factory/factory-map.tsx`
- `apps/frontend/src/components/factory/factory-map-2d.tsx`
- `apps/frontend/src/components/factory/factory-map.test.tsx`
- `apps/frontend/src/components/factory/scene/factory-scene.tsx`

## Verification

- `npm test -- --run`: passed, 22 test files and 98 tests.
- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed with all application routes generated successfully.
- Browser visual smoke testing remains manual follow-up.

## CI / Build Impact

Existing frontend CI commands cover the changed behavior; no dependencies or
workflow changes are required.

## Follow-up

Make the scene data-driven from the agreed versioned layout contract before
building the layout editor.
