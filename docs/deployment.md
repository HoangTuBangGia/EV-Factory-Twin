# Deployment

The target MVP deployment is GCP-native:

```text
Browser → Vercel Next.js → Cloud Run FastAPI → Cloud SQL PostgreSQL 17
                              ↑
                     HTTPS trusted bridge
                              ↑
                GCE ROS 2 Jazzy + Gazebo Harmonic
```

## Runtime services

During the staged cutover, `main` production remains on Render and
`c3-app-078.vercel.app` must keep its Render API/WebSocket variables. The GCP
production resources stay dark until hosted acceptance and an explicit cutover.

- `c3-app-078` and `ev-factory-twin-gcp`: isolated Vercel frontend projects.
- `ev-twin-api-dev`: Cloud Run API deployed from `develop`, with CORS limited
  to `ev-factory-twin-gcp.vercel.app`.
- `ev-twin-api`: production Cloud Run API reserved for the eventual `main`
  cutover; `develop` automation never targets it.
- `ev-twin-postgres-01`: develop Cloud SQL PostgreSQL 17.
- `ev-twin-postgres-prod-01`: production Cloud SQL PostgreSQL 17; provisioned
  separately before enabling `main` delivery.
- `ev-twin-edge-01`: develop GCE ROS/Gazebo and telemetry/command bridge.
- `ev-twin-edge-prod-01`: private production GCE ROS/Gazebo VM, provisioned and
  bootstrapped but without application code, secrets, or active services before
  cutover.

Use generated `*.run.app` and `*.vercel.app` URLs for the MVP; a custom domain
is not required.

## Backend environment

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://APP_USER:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
DATABASE_SSL_MODE=disable
AUTH_JWT_SECRET=<at-least-64-random-characters>
AUTH_JWT_ISSUER=ev-factory-twin-api
AUTH_JWT_AUDIENCE=ev-factory-twin-browser
AUTH_ACCESS_TOKEN_TTL_SECONDS=28800
EDGE_TELEMETRY_SHARED_SECRET=<independent-random-secret>
CORS_ORIGINS=https://c3-app-078.vercel.app,https://ev-factory-twin-gcp.vercel.app
MOCK_FACTORY_ENABLED=false
```

Store secrets in Secret Manager. Never put database passwords, JWT secrets, or
edge secrets in Git or frontend variables.

The Cloud Run Backend uses the dedicated `ev-twin-api` service account with
Cloud SQL Client and secret-level Secret Accessor grants. PostgreSQL connections
use the non-administrator `ev_twin_app` role provisioned before migration `0010`.
The reproducible operator flow is documented in
`docs/runbooks/gcp-cloud-run-backend.md`; use the root Make targets rather than
ad-hoc console configuration.

## Branch continuous delivery

`.github/workflows/ci.yml` calls the reusable
deployment workflows only after all CI jobs pass. `develop` deploys
`ev-twin-api-dev`; `main` deploys `ev-twin-api`. Both authenticate with separate
repository- and branch-scoped Workload Identity providers and deployers. The
shared engine builds an image tagged with the complete reviewed commit SHA and
verifies health, unauthenticated rejection, and the exact environment origin.
It then deploys the same full SHA to the matching edge VM through IAP. Develop
targets only `ev-twin-edge-01`; production targets only
`ev-twin-edge-prod-01`.

The workflow does not hold a Google service-account key. Configure the GitHub
Environment `gcp-develop` with these repository/environment variables:

```text
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/providers/github-develop
GCP_DEPLOY_SERVICE_ACCOUNT=ev-twin-github-deploy@ev-factory-twin.iam.gserviceaccount.com
```

The `gcp-production` Environment uses the `github-main` provider and
`ev-twin-github-prod-deploy` service account. Configure required reviewers on
`gcp-production` when production delivery must pause for human approval; omit
them for fully automatic delivery after protected-branch CI.

Production has its own Cloud SQL instance, runtime service account, database
credential, JWT signing secret, and edge secret. Do not activate the `main`
deployment until that database has the complete migration ledger and production
accounts/seed data.

If the deployed commit changes `postgres/migrations`, automatic deployment
stops. Apply the ledger-backed migrations to the corresponding database, then
invoke that branch's workflow manually with `migrations_applied=true`. The
workflow never applies DDL with a Backend runtime identity.

Edge delivery uses OS Login without administrator permission. The deployer may
invoke only the root-owned `/usr/local/sbin/ev-twin-deploy` command through
sudo. The wrapper validates the full SHA and repository origin, runs the ROS
gate on the VM, restarts simulation and bridge services, and rolls back on
failure.

## Frontend environment

```dotenv
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_URL=https://EV_TWIN_API.run.app
NEXT_PUBLIC_WS_URL=wss://EV_TWIN_API.run.app/ws/factory
```

## Database initialization

Create PostgreSQL 17 with the `cloudsql.enable_pg_cron=on` database flag. Cloud
SQL provides pg_cron 1.6.4 and pg_partman 5.2.4 for PostgreSQL 17; pg_partman has
no background worker there, so migration `0008` schedules its maintenance with
pg_cron. Connect as a database administrator through Cloud SQL Auth Proxy or an
authorized private client, then run:

```bash
make postgres-migrate MIGRATION_DATABASE_URL='postgresql://...'
make user-create EMAIL=designer@example.com DISPLAY_NAME='Demo Designer' ROLE=DESIGNER
make user-create EMAIL=monitor@example.com DISPLAY_NAME='Demo Monitor' ROLE=MONITOR
make postgres-seed-docker
```

`user-create` prompts twice for a password. Apply `postgres/seed.sql` only after
an active Designer exists; it contains reference layout data and no credentials.
M14.1 migration scripts target the fresh database explicitly approved for this deployment.

Migration execution is ledger-backed. `public.schema_migrations` stores the
version, filename, SHA-256 checksum, status, and applied time. A checksum change
or an interrupted `APPLYING` row stops deployment for operator review.

For the existing Cloud SQL database that already has migrations `0001` through
`0009`, create ledger entries once without replaying DDL:

```bash
make postgres-migrations-baseline-docker
make postgres-migrate-docker
```

The second command must report every migration as already applied. Do not use
the baseline target for a new or partially migrated database. After creating
the `ev_twin_app` Cloud SQL user, normal migration execution applies `0010` to
grant only runtime table and sequence access.

## Edge and acceptance

The GCE bridge uses `EDGE_TELEMETRY_SHARED_SECRET`; ROS DDS stays private. Verify
both roles, realtime telemetry, task lifecycle, scenario run, approval/apply ack,
alerts, restart persistence, and audit. Record Cloud Run revisions, Git SHA,
Cloud SQL version, and GCE services.

## Teardown

Before 2026-09-05 teardown, export required audit/results. Delete Cloud Run,
Cloud SQL, GCE, static IP, and unused firewall resources, then remove the
temporary Vercel GCP project and confirm billing stops.
