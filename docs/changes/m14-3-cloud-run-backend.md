# Cloud Run Backend

## Summary

Added the least-privilege database grant migration and reproducible GCP build,
secret, IAM, and Cloud Run deployment entry points for the FastAPI Backend.

## Motivation

The GCP-native PostgreSQL database is ready, but the Backend still needs an
immutable container deployment connected through the authenticated Cloud SQL
connector without embedding administrator credentials.

## Architecture / Contract Impact

Cloud Run uses a dedicated service account and the `ev_twin_app` PostgreSQL role.
Secrets are injected from Secret Manager. The service remains public at the
network layer while JWT and the edge shared secret enforce application access.
The MVP stays at one maximum instance because realtime fleet state is in-memory.

## Files Changed

- `postgres/migrations/0010_grant_runtime_database_access.sql`
- `deploy/gcp/cloudbuild.backend.yaml`
- `deploy/gcp/backend.env.example`
- `Makefile`
- `tests/integration/test_gcp_cloud_run_backend.py`
- `tests/integration/test_postgres_migrations.py`
- `docs/runbooks/gcp-cloud-run-backend.md`
- `docs/deployment.md`
- `docs/changes/m14-3-cloud-run-backend.md`

## Verification

- `make gcp-backend-check`: 7 migration checks and 4 Cloud Run contract checks passed.
- `make check`: Ruff, formatting, Mypy, and 389 tests passed; 2 PostgreSQL
  repository smoke tests skipped because `TEST_DATABASE_URL` was not configured.
- Enabled Cloud Run, Artifact Registry, Cloud Build, and Secret Manager APIs.
- Created the `ev-twin` Artifact Registry repository, `ev-twin-api` runtime
  service account with Cloud SQL Client, and three empty Backend secrets.
- Added the explicit Cloud Build Builder binding required because this project
  resolves builds to its Compute Engine default service account.
- Applied migration `0010` and verified the `ev_twin_app` runtime identity and
  table privileges.
- Cloud Build `af15361d-28d1-49a9-bbd8-8b7b861fc0cd` published image `93ffb17`
  with digest `sha256:fb3ab4650673156f42cdfacca9ef0d4e99c46136280f920990a432a9e0d4b1a9`.
- Cloud Run revision `ev-twin-api-00003-lkf` serves 100 percent of traffic.
  Health, unauthenticated rejection, login, and exact CORS preflight for both
  Vercel origins passed.

## CI / Build Impact

Cloud Build uses the existing locked Backend Dockerfile and publishes an image
tagged with the reviewed Git SHA. No runtime dependency is added.

## Follow-up

Deploy the Frontend to Cloud Run and run end-to-end hosted acceptance with the
GCE ROS/Gazebo edge.
