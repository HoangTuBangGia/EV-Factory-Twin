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
- Migration apply, image build, Cloud Run deploy, and hosted acceptance remain pending.

## CI / Build Impact

Cloud Build uses the existing locked Backend Dockerfile and publishes an image
tagged with the reviewed Git SHA. No runtime dependency is added.

## Follow-up

Deploy the Frontend to Cloud Run and run end-to-end hosted acceptance with the
GCE ROS/Gazebo edge.
