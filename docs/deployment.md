# Deployment

The authoritative MVP deployment is GCP-native:

```text
Browser → Cloud Run Next.js → Cloud Run FastAPI → Cloud SQL PostgreSQL 17
                                  ↑
                         HTTPS trusted bridge
                                  ↑
                    GCE ROS 2 Jazzy + Gazebo Harmonic
```

## Runtime services

- `ev-twin-web`: public Cloud Run frontend.
- `ev-twin-api`: public Cloud Run API with explicit CORS for the frontend URL.
- Cloud SQL PostgreSQL 17: private persistence; no browser access.
- `ev-twin-edge-01`: GCE ROS/Gazebo and telemetry/command bridge.

Use generated `*.run.app` URLs for the MVP; a custom domain is not required.

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
CORS_ORIGINS=https://EV_TWIN_WEB.run.app
MOCK_FACTORY_ENABLED=false
```

Store secrets in Secret Manager. Never put database passwords, JWT secrets, or
edge secrets in Git or frontend variables.

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

## Edge and acceptance

The GCE bridge uses `EDGE_TELEMETRY_SHARED_SECRET`; ROS DDS stays private. Verify
both roles, realtime telemetry, task lifecycle, scenario run, approval/apply ack,
alerts, restart persistence, and audit. Record Cloud Run revisions, Git SHA,
Cloud SQL version, and GCE services.

## Teardown

Before 2026-09-05 teardown, export required audit/results. Delete Cloud Run,
Cloud SQL, GCE, static IP, and unused firewall resources, then confirm billing stops.
