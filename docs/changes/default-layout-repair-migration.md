# Default Layout Repair Migration

## Summary

Added an append-only repair migration that creates `LAYOUT-DEFAULT` version 3
when a hosted database ran schema migrations without `seed.sql`.

## Motivation

The v2 and v3 layout migrations inserted versions with `INSERT ... SELECT` from
an existing parent layout. On an unseeded hosted database they completed without
error but inserted zero rows, causing the scenario baseline endpoint to fail.

## Architecture / Contract Impact

- The migration reuses an existing default-layout owner when available.
- If the parent is absent, the earliest active Designer becomes `created_by`.
- On a clean database where seed data has not run yet, absence of an active
  Designer emits a notice and defers default-layout creation to `seed.sql`.
- The repair is idempotent and does not update immutable version content.

## Files Changed

- Added `20260824000300_ensure_default_layout.sql`.
- Added an offline regression assertion for parent-before-version ordering and
  clean-database compatibility.

## Verification

`make migration-check`: passed all 30 PostgreSQL syntax, schema, RLS, ordering,
and repair-regression checks.

## CI / Build Impact

No application dependency or workflow changes. Hosted environments must run
`supabase db push` to apply the repair.

## Follow-up

The hosted project will contain canonical version 3 only when versions 1 and 2
were never seeded. Those historical versions are not required by the runtime.
