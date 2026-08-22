# SimPy Flow Optimization

## Summary

Added layout-bound battery-logistics simulation, nine authoritative KPI and a
deterministic bounded flow optimizer.

## Motivation

The legacy benchmark modeled only a shared robot resource and four metrics. It
could not evaluate route geometry, charging, congestion or operational tradeoffs.

## Architecture / Contract Impact

- `twin-core` owns authoritative KPI formulas.
- SimPy models individual robots, battery drain, charging and route contention.
- Every new persisted scenario binds to an immutable layout version and route.
- DESIGNER may search at most 64 deterministic combinations; every candidate is
  persisted and audited through the existing scenario workflow.
- Baseline and candidates resolve immutable layout geometry and run through the
  same logistics engine and authoritative KPI calculator.
- Backend construction requires `LayoutService`; missing layout wiring fails at
  startup/test construction instead of silently selecting a legacy engine.

## Files Changed

Added KPI, logistics, route profiling and optimization modules; extended scenario
schemas/repository/API and PostgreSQL persistence; added focused tests and docs.

## Verification

`make check` passed Ruff, format-check, Mypy and 365 tests. `make integration`
passed all 23 migration and realtime-flow integration tests. `make supabase-reset`
replayed the full migration chain and seed successfully on local PostgreSQL 17.6.
A read-only smoke query confirmed `LAYOUT-DEFAULT` version 1, all 12 new scenario
columns and the immutable layout-version foreign key. After moving baseline onto
the shared logistics engine, its focused scenario/RBAC regression suite passed
77 tests. Removing the Backend legacy fallback then passed 29 focused
scenario/mock/repository tests, and the full 365-test gate remained green.

## CI / Build Impact

Existing Python gates cover the change. The root Makefile now exposes the
previously missing `integration` target used for focused integration checks. No
dependency was added.

## Follow-up

M7 will complete submit/approval/apply command acknowledgement, timeout and audit
against the ROS2 Fleet Manager simulation.
