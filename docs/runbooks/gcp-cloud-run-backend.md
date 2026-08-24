# GCP Cloud Run Backend

## Preconditions

- Active gcloud project: `ev-factory-twin`.
- Cloud SQL `ev-twin-postgres-01` is running in `us-central1`.
- Migrations `0001` through `0009`, seed data, Designer, and Monitor exist.
- Local ADC is available for the temporary Cloud SQL Auth Proxy workflow.

## Provisioning order

Run each Make target only after human review:

```bash
make gcp-backend-apis
make gcp-artifact-repository-create
make gcp-cloud-build-access
make gcp-backend-service-account-create
make gcp-backend-cloudsql-access
make gcp-backend-secrets-create
make gcp-backend-database-user-create
```

This project uses its Compute Engine default service account as the effective
Cloud Build execution identity. `gcp-cloud-build-access` grants that identity
the predefined Cloud Build Builder role required to read staged source and push
the reviewed image. Override `GCP_CLOUD_BUILD_SERVICE_ACCOUNT` if the project's
Cloud Build default identity changes.

The database-user target prompts twice without echo, creates `ev_twin_app`, and
stores its Unix-socket `DATABASE_URL` as the first version of
`ev-twin-database-url`. It requires at least 32 characters and percent-encodes
the password before embedding it in the URI. Keep the terminal open until both
the Cloud SQL user and secret version succeed.

Start the local Cloud SQL Auth Proxy with the temporary administrator
PGPASSFILE, then apply migration `0010`:

```bash
make postgres-migrate-docker
```

Add independent JWT and edge shared-secret versions. The edge value must exactly
match `/etc/ev-factory-twin/bridge.env` on the GCE VM:

```bash
make gcp-secret-version-add SECRET_NAME=ev-twin-auth-jwt-secret
make gcp-secret-version-add SECRET_NAME=ev-twin-edge-telemetry-secret
make gcp-backend-secret-access
```

Build and deploy the immutable Git-SHA image:

```bash
make gcp-backend-build
make gcp-backend-deploy
```

Override `GCP_BACKEND_CORS_ORIGINS` during deploy when the authoritative frontend
URL differs from `https://c3-app-078.vercel.app`.

## Runtime boundaries

- Cloud Run is public at the network layer; application REST/WebSocket access is
  still enforced by JWT and edge ingress by its independent shared secret.
- The runtime service account has Cloud SQL Client and access only to the three
  Backend secrets.
- Cloud Run uses the authenticated Cloud SQL Unix socket with application-level
  TLS disabled only for that local socket.
- `min-instances=0` limits cost. `max-instances=1` preserves the current
  single-worker in-memory realtime state contract.

## Acceptance

Verify `/health`, rejected unauthenticated API access, Designer and Monitor
login, persisted layouts/scenarios, telemetry ingress, WebSocket delivery, and
restart persistence. Record the Cloud Run URL, revision, image digest, Git SHA,
and Cloud SQL connection name.
