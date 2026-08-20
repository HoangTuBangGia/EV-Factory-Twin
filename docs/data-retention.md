# Data retention and time-series decision

## Current baseline

Factory Twin uses Supabase PostgreSQL 17 for identities, roles, scenario workflow
state, layout versions, review/apply actors, business audit events, and coarse KPI
history. The advanced MVP does not persist the realtime robot telemetry stream.
Telemetry history/replay is outside the current `TOPIC.md` acceptance path.

The backend currently publishes one robot telemetry event per robot at 10 Hz.
Persisting that stream would create:

| Fleet size | Rows/second | Rows/day |
|---:|---:|---:|
| 5 robots (demo default) | 50 | 4,320,000 |
| 10 robots (current configured maximum) | 100 | 8,640,000 |

At an illustrative 0.5–1 KB per row after tuple/index overhead, the default
fleet would consume roughly 2–4 GB/day before backups and replicas. This is an
estimate, not a capacity measurement, and is why raw telemetry is outside the
MVP database scope.

`public.kpi_snapshots` is designed for one factory-wide sample every ten seconds:

- 6 rows/minute;
- 360 rows/hour;
- 8,640 rows/day;
- 259,200 rows over a 30-day detailed retention window.

The backend runtime writer is enabled only when `DATABASE_URL` is configured.
Its first sample is written after ten seconds, then it follows ten-second
wall-clock deadlines independently of simulation speed. Each sample is one
factory-wide row containing the current aggregate metrics and simulated elapsed
time; `scenario_id` remains null for the MVP. Robot pose, velocity, and other
raw telemetry are never included.

Writes are serialized by a single background worker. A slow write cannot
overlap the next one, missed deadlines are skipped instead of creating a burst,
and a database error is logged and retried at the next cadence without stopping
the mock factory or API. The worker is cancelled and awaited before database
shutdown.

Position history is not written. If it becomes a product requirement, the first
implementation should sample once every 5–10 seconds per robot and measure the
actual tuple/index size and query latency before enabling it broadly. Five
robots at a five-second cadence would produce 86,400 rows/day, fifty times less
than their raw 10 Hz stream.

## Initial retention policy

| Data | Initial retention |
|---|---|
| Profiles and role state | Account lifetime; soft-disable instead of delete |
| Scenarios and review/apply actors | Project lifetime |
| Business audit events | At least one year; append-only |
| Alerts and task transitions | Not persisted in the auth MVP; define when added |
| KPI snapshots | 30 days detailed; aggregate before any later deletion |
| Raw pose/velocity telemetry | Not stored |

The migration creates the schema and access policy, and the runtime writer now
populates it. The deletion/aggregation job is intentionally deferred: it must
not be enabled until the team has approved retention for its demo and
evaluation data. When enabled, the job must run under a restricted backend
role, record how many rows it aggregated/deleted, and never modify
`audit_events`.

## When to revisit PostgreSQL and pg_partman

Plain PostgreSQL with timestamp indexes is the default. Before considering a
dedicated TimescaleDB/Timescale Cloud or ClickHouse deployment, capture:

1. rows inserted per second and per day;
2. real bytes per table and index (`pg_total_relation_size`);
3. p50/p95 latency for the actual dashboard time-range queries;
4. maintenance cost for retention, vacuum, backup, and restore;
5. forecast fleet count and required history window.

Re-evaluate the storage engine only if measured PostgreSQL performance misses
an agreed target (initially p95 under 500 ms for a 24-hour KPI query) after
appropriate indexing and batching. Do not add `pg_partman` for the MVP: there is
no raw telemetry table to partition. Consider native partitioning or `pg_partman`
only after measured telemetry volume justifies maintenance complexity and the
Supabase project confirms extension/job support. The hosted project is PostgreSQL
17, so this roadmap does not assume that the deprecated Supabase TimescaleDB
extension is available.
