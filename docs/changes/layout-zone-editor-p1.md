# Visual Layout Zone Editor

## Summary

Replaced the layout editor's no-go and congestion JSON textareas with a visual
zone workflow. Designers can draw polygon boundaries on the existing 2D map,
edit zone metadata and coordinates, and remove zones without authoring JSON.

## Motivation

Raw JSON made a routine safety-layout task error-prone and paused the entire
preview whenever syntax was incomplete. Zone editing now follows the same
map-first interaction already used for stations and routes.

## Architecture / Contract Impact

- The existing immutable layout-version contract is unchanged.
- No-go zones still contain an ID and at least three points.
- Congestion zones additionally keep the existing `delay_multiplier` field.
- Map clicks reuse the existing 0.5 m snapping and factory-bound clamping.
- Route and zone drawing are mutually exclusive editor modes.
- Duplicate IDs across both zone kinds and out-of-footprint points block save.

## Files Changed

- Added `components/layout/layout-zone-editor.tsx` for zone forms and drawing controls.
- Extended `FactoryPlantMap2D` with congestion, selection, and draft overlays.
- Replaced JSON handling in `app/layouts/page.tsx` with visual editor state.
- Added layout-page regression coverage and zone-editor styling.
- Updated the P1 progress table in `docs/changes/fixUX.md`.

## Verification

Run from `apps/frontend`:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm test -- --run src/app/layouts/page.test.tsx`: 10 tests passed.
- `npm test -- --run`: 34 files and 154 tests passed.
- `npm run build`: passed; all 14 static pages generated.

## CI / Build Impact

No dependency, API, backend, database, or CI workflow changes.

## Follow-up

Complex CAD behavior such as dragging individual polygon vertices and geometric
self-intersection detection remains outside this P1 checkpoint.
