# Cloud SQL Provisioning

## Summary

Provisioned the temporary MVP Cloud SQL PostgreSQL 17 instance and added a
Docker-based migration entry point for hosts without `psql`.

## Motivation

M14.1 removed Supabase. The GCP-native runtime needs a migrated Cloud SQL database
before Backend and Frontend can move to Cloud Run.

## Architecture / Contract Impact

`ev-twin-postgres-01` is a zonal `db-f1-micro` instance in `us-central1`.
Developers connect through Cloud SQL Auth Proxy bound to localhost; the database
is not added to browser-accessible networks. Secret-free reference data lives in
`postgres/seed.sql`; accounts are provisioned separately through the password-prompting CLI.

## Files Changed

- `Makefile`
- `postgres/seed.sql`
- `docs/changes/m14-2-cloud-sql-provisioning.md`

## Verification

Cloud SQL creation, proxy connection, eight migrations, 31-table schema, 16
telemetry partitions and two cron jobs passed. Installed extensions are
`pgcrypto 1.3`, `pg_cron 1.6.7` and `pg_partman 5.4.3`. User/reference-data
provisioning passed. Runtime-history smoke passed; command smoke exposed a shared
`updated_at` trigger overwriting authoritative retry timestamps under hosted
latency. Migration `0009` fixes that boundary. Migration/seed contracts passed
6/6 and both hosted repository smoke tests passed after the fix. The final local
gate passed Ruff, formatting, Mypy and 384 tests; the same two hosted tests were
skipped locally after proxy credential cleanup.

## CI / Build Impact

No CI dependency added. `postgres-migrate-docker` applies the fresh ordered chain;
The original one-file migration target was superseded by the checksum-verified
ledger runner in M14.2.1.
Both use the pinned PostgreSQL 17 client image.

## Follow-up

Deploy Backend and Frontend to Cloud Run, then run hosted browser/edge acceptance.
