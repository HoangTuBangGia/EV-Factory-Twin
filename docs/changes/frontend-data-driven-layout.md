# Frontend Data-driven Factory Layout

## Summary

The 2D fallback and Three.js scene now render from one validated `FactoryLayout`
object instead of importing duplicated station, route, zone, and factory-size constants.

## Motivation

Hard-coded geometry prevented the frontend from previewing a different layout and
would have forced the future layout editor to rewrite scene components.

## Architecture / Contract Impact

- Added a frontend Zod schema matching the target layout contract in `docs/team-plan.md`.
- The default fixture preserves the current backend/simulator coordinates.
- `FactoryMap` accepts a layout and passes it to both renderers.
- No backend endpoint or authoritative runtime contract changed. The fixture remains
  the source until the versioned layout API is implemented.

## Files Changed

- `apps/frontend/src/schemas/factory.ts`
- `apps/frontend/src/lib/factory-layout.ts`
- `apps/frontend/src/lib/factory-layout.test.ts`
- `apps/frontend/src/components/factory/factory-map.tsx`
- `apps/frontend/src/components/factory/factory-map-2d.tsx`
- `apps/frontend/src/components/factory/scene/*`
- `apps/frontend/src/app/scene-probe/page.tsx`

## Verification

- `npm test -- --run`: passed, 22 test files and 98 tests, including layout schema,
  coordinate conversion, supplied-layout rendering, and layer controls.
- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed; `/factory`, `/layouts`, and `/scene-probe` were generated.
- Browser visual scene smoke testing remains manual follow-up.

## CI / Build Impact

Existing frontend CI covers the changed TypeScript and component behavior. No dependency
or workflow change is required.

## Follow-up

Add the versioned backend layout API, replace the fixture at the data boundary, and build
the minimal Designer 2D editor on this contract.
