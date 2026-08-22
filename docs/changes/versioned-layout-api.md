# Versioned Layout API

## Summary

Added validated factory-layout CRUD with immutable geometry/config versions,
Supabase persistence, audit events and two-role RBAC.

## Motivation

The frontend editor previously used a fixture and scenarios had no durable,
version-addressable layout input.

## Architecture / Contract Impact

- `twin-core` owns geometry, route, zone and runtime-configuration validation.
- `layouts` stores mutable identity metadata and soft-archive state.
- `layout_versions` is append-only and keyed by `(layout_id, version)`.
- DESIGNER mutates layouts; DESIGNER and MONITOR may read them.
- The canonical contract adds station-linked routes, congestion zones and robot,
  demand, speed and charger configuration.

## Files Changed

Added layout domain models, Backend schemas/repository/service/router, migration,
seed data and tests; updated API, architecture and team contract documentation.

## Verification

Unit tests cover valid and invalid geometry, route/no-go intersection, immutable
version reads, archive behavior and RBAC. Offline migration tests parse PostgreSQL
syntax and assert RLS/append-only invariants.

`supabase db reset` replayed the full migration chain and seed successfully on
local Supabase PostgreSQL 17.6. A read-only smoke query confirmed
`LAYOUT-DEFAULT` version 1 and RLS enabled on both layout tables.

## CI / Build Impact

The existing Python and migration gates cover M5. No dependency was added.

## Follow-up

Connect the frontend editor to this API and bind scenario runs to immutable
`layout_id` plus `layout_version` during the SimPy/KPI checkpoint.
