# Layout Route Network

## Summary

Expanded the canonical factory layout from one delivery polyline into a connected
route network shared by the layout editor, mock runtime, SimPy scenarios, and the
2D/3D views.

## Motivation

AMRs previously operated on one small route. Repositioning to the battery buffer
and travelling to a charger used direct lines, so robots could visually cross
equipment and layout changes had little operational effect.

## Architecture / Contract Impact

- `LayoutRoute.kind` distinguishes `DELIVERY` scenario flows from `SUPPORT`
  connectivity and defaults to `DELIVERY` for stored v1/v2 content.
- `twin-core` owns deterministic shortest-path routing over shared waypoints.
- Mock task movement now contains a reposition leg and an explicit pickup index;
  charging also follows the network.
- SimPy rejects support routes as scenario flows and continues deriving distance
  and congestion from the selected delivery geometry.
- `LAYOUT-DEFAULT` v3 is append-only and retains v1/v2 history.

## Files Changed

- Added the route kind and routing helper in `packages/twin-core`.
- Added the v3 layout migration and updated Supabase seed data.
- Updated backend movement/state orchestration and regression tests.
- Added two delivery choices, a charging link, a second marriage station, route
  selection/add/remove/drawing controls, and delivery-only scenario filtering.
- Updated canonical API and architecture documentation.

## Verification

- Targeted frontend contract/editor tests: 14 passed.
- `make check`: Ruff lint and format passed, mypy passed for 89 source files,
  and 416 pytest tests passed; 2 PostgreSQL integration tests were skipped
  because `TEST_DATABASE_URL` was not configured.
- `make frontend-check`: ESLint and TypeScript passed, all 109 Vitest tests
  passed, and the Next.js 15.5.23 production build completed successfully.

## CI / Build Impact

No dependency or workflow changes. Existing Python and frontend CI gates cover
the changed contract, runtime, simulation, and editor behavior.

## Follow-up

- The route network uses exact shared waypoints and bidirectional edges; one-way
  lanes, capacities, reservations, and collision avoidance remain future work.
- No-go and congestion polygons remain JSON-edited in this checkpoint.
- ROS/Nav2 still requires an edge-side topology adapter before arbitrary route
  networks can be applied to Gazebo or physical AMRs.
