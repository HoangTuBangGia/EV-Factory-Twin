# Frontend Layout Editor

## Summary

Added a Designer-only, form-based 2D layout editor for factory dimensions, station
coordinates, and route waypoints with immediate validated preview.

## Motivation

The MVP needs a bounded way to prepare layout candidates without introducing a CAD
tool or coupling the browser directly to ROS/Gazebo.

## Architecture / Contract Impact

- The editor uses the shared frontend `FactoryLayout` schema and data-driven renderer.
- Coordinates use metres and 0.5 m input steps.
- Invalid out-of-bounds drafts pause preview and show a validation error.
- The editor intentionally does not persist or apply layouts until the backend exposes
  the agreed versioned layout API.

## Files Changed

- `apps/frontend/src/app/layouts/page.tsx`
- `apps/frontend/src/app/layouts/page.test.tsx`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/components/layout/sidebar.tsx`

## Verification

- `npm test -- --run`: passed, 22 test files and 98 tests. Layout editor tests cover
  station updates/reset, route waypoint add/remove, and Designer authorization.
- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed and generated the `/layouts` route successfully.
- Browser visual smoke testing remains manual follow-up.

## CI / Build Impact

Existing frontend CI covers the new route and tests. No dependency or workflow change
is required.

## Follow-up

Connect save/version actions to the backend layout API, then bind scenario runs to an
immutable layout version.
