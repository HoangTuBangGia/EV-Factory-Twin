# Runtime Health and Retention

## Summary

Added persistent runtime alerts, bridge/task/telemetry history, health sweeps and
bounded PostgreSQL retention managed by pg_partman and pg_cron.

## Motivation

ROS telemetry previously updated only process memory. Bridge disconnects, stale
robots and command timeouts were not durable or visible through the alert contract.

## Architecture / Contract Impact

- Late telemetry is persisted but never overwrites a newer robot snapshot.
- Alerts use UUID occurrences and a stable active dedupe key with clear/retrigger.
- Health sweeps cover stale robot telemetry and stale/degraded bridges.
- Command retries clear timeout alerts; another timeout retriggers a new occurrence.
- Congestion uses moving-robot proximity for the MVP. Active-layout zone occupancy
  is the documented upgrade boundary.
- Daily telemetry partitions retain 30 days; alert/task/KPI history retains 90 days.

## Files Changed

Added runtime history/health services and migration; updated ingress, commands,
MOCK alert persistence, API schemas, configuration, tests and canonical docs.

## Verification

- Targeted M8 tests: 64 passed.
- `make check`: Ruff, format-check and Mypy passed; 384 tests passed and the
  database-gated smoke skipped as designed.
- `make supabase-reset`: all migrations and seed applied successfully.
- Local PostgreSQL: pg_partman 5.3.1, pg_cron 1.6.4, 16 telemetry partitions,
  30-day partman retention and both named cron jobs verified.
- PostgreSQL repository smoke: 1 passed with test data cleanup.
- `git diff --check`: passed.

## CI / Build Impact

No application dependency added. Supabase must provide pg_partman 5.3.1 and
pg_cron 1.6.4; the hosted project capability was confirmed before implementation.

## Follow-up

Bind runtime congestion to the APPLIED layout's congestion-zone occupancy when
the live runtime gains an authoritative active-layout projection.
