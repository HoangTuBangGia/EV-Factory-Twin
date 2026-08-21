# Data retention and time-series decision

## MVP decision

The target database is Supabase PostgreSQL 17.6.1.155. The MVP persists the
telemetry history needed for stale detection, incident investigation and KPI
calculation; it does not promise indefinite raw 10 Hz retention or a complete
incident-replay UI.

Telemetry storage must be sampled or batched at an explicitly configured cadence.
The source timestamp, ingest timestamp and `robot_id` form the ordering/isolation
boundary. Late samples may be stored for history but must not overwrite a newer
runtime snapshot.

## Initial retention contract

| Data | Initial policy |
|---|---|
| Profiles and role state | Account lifetime; inactive instead of product-side deletion |
| Immutable layout versions | Project lifetime |
| Scenarios, simulation runs and KPI results | Project lifetime |
| Approval, command and business audit events | At least one year; append-only where applicable |
| Alerts and task transitions | 90 days |
| Detailed robot telemetry | 30 days |
| KPI snapshots | 90 days |

These values are contract defaults, not yet implemented retention jobs. A later
checkpoint must measure row size, write rate and the dashboard's p95 time-range
query latency before finalizing the telemetry sampling cadence.

## pg_partman gate

The requested implementation uses time-based PostgreSQL partitions managed by
`pg_partman` for robot telemetry. Before writing that migration against the hosted
project, verify all of the following on Supabase PostgreSQL 17.6.1.155:

1. the extension and compatible version are available;
2. the migration role can create/configure it;
3. Supabase can schedule partition maintenance and retention;
4. backup/restore includes partitioned data and configuration.

If any condition fails, stop and request approval for native declarative
partitioning plus a scheduled retention function. Do not silently create a
non-partitioned high-volume telemetry table.

## Capacity verification

Record rows/second, bytes per table/index, maintenance duration, backup size and
p50/p95 query latency. The initial query target is p95 below 500 ms for a 24-hour
single-robot telemetry window. Retention jobs must log affected partitions/rows
and must never modify business audit events.
