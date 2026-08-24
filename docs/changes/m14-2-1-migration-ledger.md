# PostgreSQL Migration Ledger

## Summary

Added a checksum-verified PostgreSQL migration ledger and a one-time baseline
workflow for the existing Cloud SQL `0001` through `0009` schema.

## Motivation

The initial GCP-native provisioning applied ordered SQL files directly. Future
migrations need deterministic skip, tamper detection, and interrupted-run detection.

## Architecture / Contract Impact

`public.schema_migrations` records version, filename, SHA-256 checksum, status and
application time. The runner skips matching `APPLIED` files, rejects checksum
drift, and fails closed on `APPLYING` rows that require operator recovery. It
loads existing ledger records once so Cloud SQL latency does not grow by one
read connection per migration.

## Files Changed

- `scripts/postgres_migrate.sh`
- `Makefile`
- `tests/integration/test_postgres_migrations.py`
- `docs/development.md`
- `docs/deployment.md`
- `docs/changes/m14-2-1-migration-ledger.md`

## Verification

- `make migration-check`: 7 passed.
- `make check`: Ruff, formatting, Mypy, and 385 tests passed; 2 PostgreSQL
  repository smoke tests skipped because `TEST_DATABASE_URL` was not configured.
- Cloud SQL baseline recorded and checksum-verified migrations `0001` through
  `0009`.
- `make postgres-migrate-docker`: all 9 migrations skipped as already applied.

## CI / Build Impact

No dependency added. The runner executes inside the existing PostgreSQL 17
client container.

## Follow-up

Begin Cloud Run Backend deployment.
