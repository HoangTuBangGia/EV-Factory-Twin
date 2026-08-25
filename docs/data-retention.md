# Data retention and time-series decision

## MVP decision

The target database is Cloud SQL PostgreSQL 17. The MVP persists the
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

M8 implements these defaults: pg_partman drops telemetry partitions older than
30 days, while a daily retention function prunes alerts, task transitions and KPI
snapshots older than 90 days. Capacity measurements remain a deployment gate for
finalizing the telemetry sampling cadence.

## pg_partman decision

The provisioned Cloud SQL PostgreSQL 17 instance uses pg_cron 1.6.7 and
pg_partman 5.4.3. M8 uses time-based PostgreSQL partitions managed by pg_partman
for robot telemetry. Deployment must still verify:

1. the migration role can create/configure both extensions;
2. scheduled maintenance succeeds and remains observable;
3. backup/restore includes partitioned data and configuration.

If any condition fails, stop and request approval for native declarative
partitioning plus a scheduled retention function. Do not silently create a
non-partitioned high-volume telemetry table.

## Capacity verification

Record rows/second, bytes per table/index, maintenance duration, backup size and
p50/p95 query latency. The initial query target is p95 below 500 ms for a 24-hour
single-robot telemetry window. Retention jobs must log affected partitions/rows
and must never modify business audit events.
