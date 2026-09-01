# GCP Operations Runbook

## Scope

This is the operator command reference for the isolated GCP-native MVP stack:

```text
Vercel feature deployment
  -> Cloud Run FastAPI
  -> Cloud SQL PostgreSQL 17
  <- GCE ROS 2 / Gazebo telemetry bridge
```

The project is `ev-factory-twin`, the primary region is `us-central1`, and the
edge VM zone is `us-central1-a`. Until the explicit cutover, the `main`/Render
production stack remains live and must not be changed by GCP preparation.

Run commands one block at a time and inspect their output. Commands marked
**destructive** require explicit human review immediately before execution.
Never commit or print credentials, database URLs, JWT secrets, or edge shared
secrets.

Related runbooks:

- [GCP cost control](gcp-cost-control.md)
- [GCP edge](gcp-edge.md)
- [GCP Cloud Run Backend](gcp-cloud-run-backend.md)

## 1. Local gcloud session

Check the CLI, authenticated identities, ADC, project, and billing:

```bash
gcloud version
gcloud auth list
gcloud auth application-default print-access-token >/dev/null
gcloud config get-value project
gcloud projects describe ev-factory-twin
gcloud billing projects describe ev-factory-twin
```

Login only when the corresponding check fails:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project ev-factory-twin
```

List enabled APIs:

```bash
gcloud services list \
  --project=ev-factory-twin \
  --enabled \
  --format='table(config.name)'
```

Enable the Backend APIs through the reviewed Makefile target:

```bash
make gcp-backend-apis
```

## 2. Whole-project inventory

Run these read-only commands before maintenance or teardown:

```bash
gcloud compute instances list --project=ev-factory-twin
gcloud compute disks list --project=ev-factory-twin
gcloud compute addresses list --project=ev-factory-twin
gcloud compute snapshots list --project=ev-factory-twin
gcloud compute networks list --project=ev-factory-twin
gcloud compute networks subnets list --project=ev-factory-twin
gcloud compute firewall-rules list --project=ev-factory-twin
gcloud compute routers list --project=ev-factory-twin
gcloud sql instances list --project=ev-factory-twin
gcloud run services list --project=ev-factory-twin --region=us-central1
gcloud artifacts repositories list --project=ev-factory-twin --location=us-central1
gcloud secrets list --project=ev-factory-twin
gcloud iam service-accounts list --project=ev-factory-twin
```

Console entry points:

- [Project dashboard](https://console.cloud.google.com/home/dashboard?project=ev-factory-twin)
- [Billing reports](https://console.cloud.google.com/billing/reports?project=ev-factory-twin)
- [Compute Engine](https://console.cloud.google.com/compute/instances?project=ev-factory-twin)
- [Cloud SQL](https://console.cloud.google.com/sql/instances?project=ev-factory-twin)
- [Cloud Run](https://console.cloud.google.com/run?project=ev-factory-twin)
- [Artifact Registry](https://console.cloud.google.com/artifacts?project=ev-factory-twin)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=ev-factory-twin)

## 3. Edge VM lifecycle and IAP

Inspect, start, or stop the environment-specific VM. Use `ev-twin-edge-01` for
develop and `ev-twin-edge-prod-01` for production:

```bash
gcloud compute instances describe ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --format='yaml(name,status,machineType,disks,networkInterfaces,serviceAccounts,scheduling)'

gcloud compute instances start ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a

gcloud compute instances stop ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a
```

The production VM is private, uses IAP SSH and Cloud NAT, and has deletion
protection. Provision and bootstrap it from the operator machine with:

```bash
make gcp-production-edge-vm-create
make gcp-edge-router-create
make gcp-edge-nat-create
make gcp-production-edge-bootstrap
```

The bootstrap installs ROS 2 Jazzy and Gazebo Harmonic but deliberately does
not clone code, read production secrets, or enable services.

Stopping interrupts telemetry and command execution but preserves the boot
disk. Disk charges continue until the disk is deleted.

Open an interactive SSH session through IAP:

```bash
gcloud compute ssh ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --tunnel-through-iap
```

Run one command without an interactive shell:

```bash
gcloud compute ssh ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --tunnel-through-iap \
  --command='hostname && uptime'
```

Copy a file to or from the VM:

```bash
gcloud compute scp \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --tunnel-through-iap \
  LOCAL_FILE \
  ev-twin-edge-01:/tmp/REMOTE_FILE

gcloud compute scp \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --tunnel-through-iap \
  ev-twin-edge-01:/tmp/REMOTE_FILE \
  LOCAL_FILE
```

Replace placeholders with explicit files. Do not copy private credentials into
the repository.

## 4. Deploy an accepted ROS commit

The accepted commit may come from `feat/gcp-native-stack`; it does not have to
be merged into `main`. Use a full immutable SHA after its CI passes.

On the VM:

```bash
sudo systemctl stop ev-twin-bridge.service ev-twin-simulation.service
sudo -u ev-twin git -C /opt/ev-factory-twin fetch origin feat/gcp-native-stack
sudo -u ev-twin git -C /opt/ev-factory-twin checkout --detach ACCEPTED_COMMIT_SHA
sudo -u ev-twin git -C /opt/ev-factory-twin rev-parse HEAD
```

The last output must exactly equal `ACCEPTED_COMMIT_SHA`.

Build and test ROS as the runtime user:

```bash
sudo -u ev-twin bash -lc '
cd /opt/ev-factory-twin
source /opt/ros/jazzy/setup.bash
make ros-check
'
```

Install the versioned systemd units:

```bash
cd /opt/ev-factory-twin
sudo install -o root -g root -m 0644 \
  deploy/gcp/systemd/ev-twin-simulation.service \
  /etc/systemd/system/ev-twin-simulation.service
sudo install -o root -g root -m 0644 \
  deploy/gcp/systemd/ev-twin-bridge.service \
  /etc/systemd/system/ev-twin-bridge.service
sudo systemctl daemon-reload
```

## 5. Configure the telemetry bridge

The bridge connects only to Cloud Run over outbound HTTPS. It does not connect
to Cloud SQL and must not receive database credentials.

Expected `/etc/ev-factory-twin/bridge.env` values:

```dotenv
EV_TWIN_ROOT=/opt/ev-factory-twin
ROS_DOMAIN_ID=42
TELEMETRY_BACKEND_URL=https://ev-twin-api-849232336681.us-central1.run.app
EDGE_TELEMETRY_SHARED_SECRET=<same value as GCP Secret Manager>
BRIDGE_ID=gcp-edge-main
```

Both systemd services also read `/etc/ev-factory-twin/runtime.env`. Start from
`deploy/gcp/runtime.env.example` and keep the layout/version/route/config values
identical to the approved scenario. A topology change is not complete until the
simulation and bridge have both restarted with that file and the Backend
compatibility endpoint reports `LIVE_APPLY`.

```bash
sudo install -o root -g root -m 0644 \
  /opt/ev-factory-twin/deploy/gcp/runtime.env.example \
  /etc/ev-factory-twin/runtime.env
sudoedit /etc/ev-factory-twin/runtime.env
```

On the operator machine, retrieve the secret without printing it and copy it
through IAP:

```bash
umask 077
gcloud secrets versions access latest \
  --secret=ev-twin-edge-telemetry-secret \
  --project=ev-factory-twin \
  > /tmp/ev-twin-edge-secret

gcloud compute scp \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --tunnel-through-iap \
  /tmp/ev-twin-edge-secret \
  ev-twin-edge-01:/tmp/ev-twin-edge-secret

shred -u /tmp/ev-twin-edge-secret
```

On the VM, materialize the root-only file without putting the secret in shell
history:

```bash
sudo bash -c '
set -eu
secret="$(tr -d "\r\n" < /tmp/ev-twin-edge-secret)"
test "${#secret}" -ge 32
install -d -o root -g root -m 0700 /etc/ev-factory-twin
install -o root -g root -m 0600 /dev/null /etc/ev-factory-twin/bridge.env
{
  printf "%s\n" \
    "EV_TWIN_ROOT=/opt/ev-factory-twin" \
    "ROS_DOMAIN_ID=42" \
    "TELEMETRY_BACKEND_URL=https://ev-twin-api-849232336681.us-central1.run.app" \
    "EDGE_TELEMETRY_SHARED_SECRET=${secret}" \
    "BRIDGE_ID=gcp-edge-main"
} > /etc/ev-factory-twin/bridge.env
rm -f /tmp/ev-twin-edge-secret
unset secret
'
```

Validate without printing the secret:

```bash
sudo bash -c '
set -a
source /etc/ev-factory-twin/bridge.env
set +a
test "$TELEMETRY_BACKEND_URL" = \
  "https://ev-twin-api-849232336681.us-central1.run.app"
test "${#EDGE_TELEMETRY_SHARED_SECRET}" -ge 32
printf "Backend: %s\nBridge: %s\nSecret length: %s\n" \
  "$TELEMETRY_BACKEND_URL" "$BRIDGE_ID" \
  "${#EDGE_TELEMETRY_SHARED_SECRET}"
'
```

Never run `cat /etc/ev-factory-twin/bridge.env` in captured output.

## 6. Operate ROS and bridge services

```bash
sudo systemctl enable ev-twin-simulation.service ev-twin-bridge.service
sudo systemctl restart ev-twin-simulation.service
sudo systemctl restart ev-twin-bridge.service

systemctl is-active ev-twin-simulation.service ev-twin-bridge.service
systemctl --no-pager --full status \
  ev-twin-simulation.service ev-twin-bridge.service

journalctl \
  -u ev-twin-simulation.service \
  -u ev-twin-bridge.service \
  --since "10 minutes ago" \
  --no-pager
```

Follow logs interactively and exit with Ctrl-C:

```bash
journalctl -f -u ev-twin-simulation.service -u ev-twin-bridge.service
```

Restart only the bridge after changing its environment:

```bash
sudo systemctl restart ev-twin-bridge.service
```

Inspect resource use:

```bash
free -h
df -h /
du -sh /home/ev-twin/.ros/log /var/log/journal \
  /opt/ev-factory-twin/ros2_ws/build \
  /opt/ev-factory-twin/ros2_ws/install \
  /opt/ev-factory-twin/ros2_ws/log
ps -eo pid,comm,%cpu,%mem,rss --sort=-rss | head -15
systemctl show ev-twin-simulation.service ev-twin-bridge.service \
  --property=MemoryCurrent --property=CPUUsageNSec --property=NRestarts
```

## 7. Inspect the ROS graph

```bash
sudo -u ev-twin bash -lc '
source /opt/ros/jazzy/setup.bash
source /opt/ev-factory-twin/ros2_ws/install/setup.bash
ros2 node list
'

sudo -u ev-twin bash -lc '
source /opt/ros/jazzy/setup.bash
source /opt/ev-factory-twin/ros2_ws/install/setup.bash
ros2 topic list |
grep -E "^/amr_0[12]/(cmd_vel|odom|tf|battery_state|status|task_id|payload_id)$"
'

sudo -u ev-twin bash -lc '
source /opt/ros/jazzy/setup.bash
source /opt/ev-factory-twin/ros2_ws/install/setup.bash
timeout 10 ros2 topic echo --once /amr_01/odom
'
```

## 8. Cloud Run Backend

Get the URL, revision, image, and traffic:

```bash
gcloud run services describe ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format='yaml(status.url,status.latestCreatedRevisionName,status.latestReadyRevisionName,status.traffic,spec.template.spec.containers[0].image)'
```

Health and authentication boundary checks:

```bash
curl --fail --silent --show-error \
  https://ev-twin-api-849232336681.us-central1.run.app/health

curl --silent --show-error \
  --output /dev/null \
  --write-out '%{http_code}\n' \
  https://ev-twin-api-849232336681.us-central1.run.app/api/v1/factory
```

Expected unauthenticated API result: `401`.

Inspect ordinary environment variables and secret references separately:

```bash
gcloud run services describe ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format=json |
jq -r '.spec.template.spec.containers[0].env[] | select(has("value")) | [.name,.value] | @tsv'

gcloud run services describe ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format=json |
jq -r '.spec.template.spec.containers[0].env[] | select(has("valueFrom")) | [.name,.valueFrom.secretKeyRef.name,.valueFrom.secretKeyRef.key] | @tsv'
```

Read logs and list revisions:

```bash
gcloud run services logs read ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --limit=100

gcloud run revisions list \
  --project=ev-factory-twin \
  --region=us-central1 \
  --service=ev-twin-api
```

Verify one Vercel origin at a time:

```bash
curl --silent --show-error --dump-header - --output /dev/null \
  --request OPTIONS \
  --header 'Origin: https://c3-app-078.vercel.app' \
  --header 'Access-Control-Request-Method: GET' \
  https://ev-twin-api-849232336681.us-central1.run.app/api/v1/factory |
grep -i '^access-control-allow-origin:'

curl --silent --show-error --dump-header - --output /dev/null \
  --request OPTIONS \
  --header 'Origin: https://ev-factory-twin-gcp.vercel.app' \
  --header 'Access-Control-Request-Method: GET' \
  https://ev-twin-api-849232336681.us-central1.run.app/api/v1/factory |
grep -i '^access-control-allow-origin:'
```

## 9. Build and deploy the Backend

Verify locally, build an immutable Git-SHA image, then deploy:

```bash
make gcp-backend-check
make check
git rev-parse --short HEAD
make gcp-backend-build
make gcp-backend-deploy \
  GCP_BACKEND_CORS_ORIGINS=https://c3-app-078.vercel.app,https://ev-factory-twin-gcp.vercel.app
```

Deployment creates a Cloud Run revision and affects the isolated GCP feature
environment. It does not deploy Render. Repeat health, `401`, CORS, revision,
and login checks afterward.

Inspect images and build history:

```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/ev-factory-twin/ev-twin/backend \
  --include-tags

gcloud builds list \
  --project=ev-factory-twin \
  --limit=20 \
  --format='table(id,status,createTime,duration,images)'
```

### Develop CI/CD bootstrap

The develop deployment uses GitHub OIDC and Workload Identity Federation. It
does not use a downloaded service-account key. Run the following targets once
from an authenticated operator workstation:

```bash
make gcp-develop-cicd-apis
make gcp-develop-cicd-service-account-create
make gcp-develop-cicd-wif-create
make gcp-develop-cicd-access
```

Resolve the provider identifier without exposing a secret:

```bash
gcloud iam workload-identity-pools providers describe github-develop \
  --project=ev-factory-twin \
  --location=global \
  --workload-identity-pool=github-actions \
  --format='value(name)'
```

In the GitHub `gcp-develop` Environment, create variables:

```text
GCP_WORKLOAD_IDENTITY_PROVIDER=<provider name returned above>
GCP_DEPLOY_SERVICE_ACCOUNT=ev-twin-github-deploy@ev-factory-twin.iam.gserviceaccount.com
```

After both branch deployers exist, create/configure both GitHub Environments in
one operator-controlled command and inspect the non-secret variables:

```bash
make github-gcp-environments-configure
make github-gcp-environments-list
```

Before enabling automatic deployment, bootstrap the public develop service once
with operator credentials and an already reviewed image:

```bash
make gcp-backend-deploy \
  GCP_BACKEND_SERVICE=ev-twin-api-dev \
  GCP_BACKEND_CORS_ORIGINS=https://ev-factory-twin-gcp.vercel.app
```

This one-time command sets the public invoker policy. The GitHub deployer has
Cloud Run Developer rather than Cloud Run Admin and therefore updates revisions
without changing service IAM.

Verify the same hosted contract enforced by CI/CD:

```bash
make gcp-backend-smoke \
  GCP_BACKEND_SERVICE=ev-twin-api-dev \
  GCP_BACKEND_CORS_ORIGINS=https://ev-factory-twin-gcp.vercel.app
```

After a successful `develop` CI run, `.github/workflows/deploy-gcp-develop.yml`
publishes the full-SHA image, deploys only `ev-twin-api-dev`, verifies it, then
deploys the same SHA to `ev-twin-edge-01`. It does not target `ev-twin-api`,
`main`, `ev-twin-edge-prod-01`, or either Vercel project. Vercel continues to
deploy its configured branch independently.

Bootstrap edge access once after creating the deploy identity. These operations
grant project read/IAP access but OS Login only on the selected VM:

```bash
make gcp-edge-cicd-access
make gcp-edge-os-login-enable
make gcp-edge-operator-impersonation-grant OPERATOR_ACCOUNT=OPERATOR_EMAIL
make gcp-edge-deploy-os-user
```

Use the username printed by the last command to install the reviewed wrapper
and its single-command sudo rule:

```bash
make gcp-edge-deploy-wrapper-install EDGE_DEPLOY_OS_USER=USERNAME_FROM_PREVIOUS_COMMAND
make gcp-edge-operator-impersonation-revoke OPERATOR_ACCOUNT=OPERATOR_EMAIL
```

The temporary Token Creator binding exists only so the operator workstation can
impersonate the deploy identity during bootstrap. Revoke it immediately after
installing and validating the wrapper; GitHub WIF does not require it.

Repeat for production with explicit overrides; this prepares access but does
not deploy or start production:

```bash
make gcp-edge-cicd-access \
  GCP_EDGE_VM=ev-twin-edge-prod-01 \
  GCP_EDGE_DEPLOY_SERVICE_ACCOUNT_EMAIL=ev-twin-github-prod-deploy@ev-factory-twin.iam.gserviceaccount.com
make gcp-edge-os-login-enable GCP_EDGE_VM=ev-twin-edge-prod-01
make gcp-edge-deploy-os-user \
  GCP_EDGE_DEPLOY_SERVICE_ACCOUNT_EMAIL=ev-twin-github-prod-deploy@ev-factory-twin.iam.gserviceaccount.com
make gcp-edge-deploy-wrapper-install \
  GCP_EDGE_VM=ev-twin-edge-prod-01 \
  EDGE_DEPLOY_OS_USER=PRODUCTION_USERNAME_FROM_PREVIOUS_COMMAND
```

If migrations changed, first apply them through the existing operator-controlled
Cloud SQL proxy flow. Then dispatch `Deploy GCP Develop` from branch `develop`
with `migrations_applied=true`. Do not use this confirmation before checking the
migration ledger.

Inspect the resulting revision:

```bash
gcloud run services describe ev-twin-api-dev \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format='yaml(status.url,status.latestReadyRevisionName,status.traffic,spec.template.spec.containers[0].image)'
```

ROS/Gazebo VM deployment remains operator-approved. Do not grant the GitHub
Backend deployer general SSH or sudo access. A later edge deployment checkpoint
must install a narrowly scoped VM deployment wrapper before adding an approved
GitHub Environment job.

### Production CI/CD bootstrap

Production uses a second Cloud SQL instance and independent runtime/deployment
identities. Create resources in this order:

```bash
make gcp-production-cloudsql-create
make gcp-production-postgres-password-set
make gcp-production-backend-service-account-create
make gcp-production-backend-cloudsql-access
make gcp-production-secrets-create
make gcp-production-database-user-create
make gcp-secret-version-add SECRET_NAME=ev-twin-prod-auth-jwt-secret
make gcp-secret-version-add SECRET_NAME=ev-twin-prod-edge-telemetry-secret
make gcp-production-backend-secret-access
```

The Cloud SQL create target provisions a separate zonal PostgreSQL 17 Enterprise
`db-f1-micro` instance with pg_cron enabled. The explicit edition prevents the
CLI defaulting PostgreSQL 17 to Enterprise Plus, which does not support this
shared-core tier. It starts billing immediately. The password targets prompt
without echo and never write credentials to the repository.

Connect the Auth Proxy to
`ev-factory-twin:us-central1:ev-twin-postgres-prod-01`, prepare a matching
root-only `CLOUD_SQL_PGPASSFILE`, then apply the full migration chain and seed
production accounts/reference data. Do not baseline a fresh production
database.

The Makefile keeps the administrator password out of shell history:

```bash
make gcp-production-pgpassfile-create
make gcp-production-cloudsql-proxy-start
make postgres-migrate-docker \
  CLOUD_SQL_PGPASSFILE=/tmp/ev-twin-production-cloudsql.pgpass
```

After migration, create both production roles. Each command prompts for the
browser password twice without printing it:

```bash
make gcp-production-user-create \
  EMAIL=designer@example.com DISPLAY_NAME='Production Designer' ROLE=DESIGNER
make gcp-production-user-create \
  EMAIL=monitor@example.com DISPLAY_NAME='Production Monitor' ROLE=MONITOR
make gcp-production-seed
make gcp-production-postgres-smoke
```

The wrapper reads the runtime database URL from Secret Manager, replaces only
its Cloud Run socket with the local proxy address, disables database TLS only
for that localhost proxy hop, and does not print the URL. The proxy-to-Cloud SQL
connection remains authenticated and encrypted. After seed and smoke operations,
always stop the proxy and securely remove the temporary password file:

```bash
make gcp-production-cloudsql-proxy-stop
```

Create the production GitHub identity after the database is ready:

```bash
make gcp-production-cicd-service-account-create
make gcp-production-cicd-wif-create
make gcp-production-cicd-access
```

Resolve the `github-main` provider name and configure it with the production
deployer in the `gcp-production` GitHub Environment:

```text
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/849232336681/locations/global/workloadIdentityPools/github-actions/providers/github-main
GCP_DEPLOY_SERVICE_ACCOUNT=ev-twin-github-prod-deploy@ev-factory-twin.iam.gserviceaccount.com
```

Bootstrap the public production service once using an accepted image:

```bash
make gcp-backend-deploy \
  GCP_BACKEND_SERVICE=ev-twin-api \
  GCP_BACKEND_SERVICE_ACCOUNT=ev-twin-api-prod \
  GCP_CLOUD_SQL_INSTANCE=ev-twin-postgres-prod-01 \
  GCP_DATABASE_URL_SECRET=ev-twin-prod-database-url \
  GCP_AUTH_JWT_SECRET=ev-twin-prod-auth-jwt-secret \
  GCP_EDGE_SECRET=ev-twin-prod-edge-telemetry-secret \
  GCP_BACKEND_CORS_ORIGINS=https://c3-app-078.vercel.app
```

Only after this bootstrap and hosted smoke should `main` delivery be enabled.
Until the cutover, do not change the `c3-app-078` Render variables and do not
start the production ROS bridge.
Use required reviewers on `gcp-production` for an approval gate, or omit them
for automatic deployment after protected-branch CI.

## 10. Cloud SQL and Auth Proxy

Inspect Cloud SQL without connecting:

```bash
gcloud sql instances describe ev-twin-postgres-01 \
  --project=ev-factory-twin \
  --format='yaml(name,state,region,databaseVersion,settings.tier,settings.dataDiskSizeGb,settings.dataDiskType,settings.backupConfiguration,connectionName,ipAddresses)'

gcloud sql users list \
  --project=ev-factory-twin \
  --instance=ev-twin-postgres-01

gcloud sql databases list \
  --project=ev-factory-twin \
  --instance=ev-twin-postgres-01
```

Start a local Auth Proxy on `127.0.0.1:5433`:

```bash
docker run --detach --rm \
  --name ev-twin-cloud-sql-proxy \
  --user "$(id -u):$(id -g)" \
  --network host \
  --volume "$HOME/.config/gcloud/application_default_credentials.json:/credentials.json:ro" \
  gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.18.2 \
  --credentials-file=/credentials.json \
  --address=127.0.0.1 \
  --port=5433 \
  ev-factory-twin:us-central1:ev-twin-postgres-01

docker logs ev-twin-cloud-sql-proxy
```

Stop and automatically remove it:

```bash
docker stop ev-twin-cloud-sql-proxy
```

The proxy authenticates the connection path; PostgreSQL still requires a
database username and password.

## 11. Migrations and PostgreSQL smoke

Create the temporary administrator PGPASSFILE without shell-history exposure:

```bash
umask 077
read -rsp 'Cloud SQL postgres password: ' postgres_password
printf '\n'
printf '127.0.0.1:5433:postgres:postgres:%s\n' "$postgres_password" \
  > /tmp/ev-twin-cloudsql.pgpass
unset postgres_password
```

With the proxy running, apply only pending checksum-verified migrations:

```bash
make postgres-migrate-docker
```

Do not use `postgres-migrations-baseline-docker` on a new or partially migrated
database. It is only for an already-proven historical database.

Inspect the ledger:

```bash
docker run --rm --network host \
  --env PGPASSFILE=/run/secrets/pgpass \
  --volume /tmp/ev-twin-cloudsql.pgpass:/run/secrets/pgpass:ro \
  postgres:17-alpine \
  psql --host=127.0.0.1 --port=5433 \
    --username=postgres --dbname=postgres \
    --command='select version, filename, status, applied_at from public.schema_migrations order by version;'
```

Run the two repository smoke tests with the application role:

```bash
database_url="$(
  gcloud secrets versions access latest \
    --secret=ev-twin-database-url \
    --project=ev-factory-twin
)"

local_database_url="$(
  printf '%s' "$database_url" |
    sed 's#@/postgres?host=/cloudsql/[^[:space:]]*$#@127.0.0.1:5433/postgres#'
)"

TEST_DATABASE_URL="$local_database_url" make postgres-smoke
unset database_url local_database_url
```

Expected result: `2 passed`. Do not print either URL. Clean up afterward:

```bash
shred -u /tmp/ev-twin-cloudsql.pgpass
docker stop ev-twin-cloud-sql-proxy
```

## 12. Secrets, IAM, and networking

List metadata without secret payloads:

```bash
gcloud secrets list --project=ev-factory-twin
gcloud secrets versions list ev-twin-database-url --project=ev-factory-twin
gcloud secrets versions list ev-twin-auth-jwt-secret --project=ev-factory-twin
gcloud secrets versions list ev-twin-edge-telemetry-secret --project=ev-factory-twin
```

Inspect the Backend service account's project roles:

```bash
gcloud projects get-iam-policy ev-factory-twin \
  --flatten='bindings[].members' \
  --filter='bindings.members:serviceAccount:ev-twin-api@ev-factory-twin.iam.gserviceaccount.com' \
  --format='table(bindings.role)'
```

Add a reviewed secret version interactively:

```bash
make gcp-secret-version-add SECRET_NAME=SECRET_NAME
```

Inventory networking:

```bash
gcloud compute networks list --project=ev-factory-twin
gcloud compute networks subnets list --project=ev-factory-twin
gcloud compute firewall-rules list --project=ev-factory-twin
gcloud compute addresses list --project=ev-factory-twin
gcloud compute routers list --project=ev-factory-twin
```

The edge needs outbound TCP 443 and IAP SSH. Never expose ROS DDS, Gazebo,
PostgreSQL, or bridge ports publicly.

## 13. Hosted acceptance

Use `https://ev-factory-twin-gcp.vercel.app`, not the Render-backed production
frontend. Verify:

1. Cloud Run health succeeds and unauthenticated application data returns 401.
2. Designer and Monitor can log in through GCP-native auth.
3. Both edge services are active and the ROS graph contains two namespaces.
4. `AMR-01` and `AMR-02` appear separately over REST and WebSocket.
5. A task completes pickup, delivery, and charging.
6. Telemetry persists through a Cloud Run cold start.
7. Designer submits a scenario and Monitor approves/applies it.
8. Command state reaches `PENDING -> ACKNOWLEDGED -> COMPLETED`.
9. With the edge stopped, command timeout and disconnect alerts appear.
10. After restart and explicit retry, a new immutable attempt completes.

Record the Git SHA, Cloud Run revision, image digest, Cloud SQL version, GCE
service status, and test evidence without secrets.

## 14. Troubleshooting shortcuts

IAP SSH:

```bash
gcloud compute instances describe ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a \
  --format='value(status)'

gcloud compute firewall-rules list \
  --project=ev-factory-twin \
  --filter='sourceRanges:35.235.240.0/20'
```

Bridge HTTP 409 can mean the Backend mock source is active:

```bash
gcloud run services describe ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format=json |
jq -r '.spec.template.spec.containers[0].env[] | select(.name == "MOCK_FACTORY_ENABLED") | .value'
```

Expected value: `false`. A stale command lease can also return 409; inspect its
operation ID and Backend logs before retrying.

Bridge or ROS failure:

```bash
systemctl is-active ev-twin-simulation.service ev-twin-bridge.service
journalctl -u ev-twin-bridge.service --since "10 minutes ago" --no-pager
```

Cloud Run startup failure:

```bash
gcloud run services logs read ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --limit=100
```

Cloud SQL Proxy failure:

```bash
docker ps --filter name=ev-twin-cloud-sql-proxy
docker logs ev-twin-cloud-sql-proxy
gcloud auth application-default print-access-token >/dev/null
gcloud sql instances describe ev-twin-postgres-01 \
  --project=ev-factory-twin \
  --format='value(state)'
```

## 15. Backup and teardown

Create and verify a final backup before destructive teardown:

```bash
gcloud sql backups create \
  --project=ev-factory-twin \
  --instance=ev-twin-postgres-01 \
  --description='Final MVP backup before teardown'

gcloud sql backups list \
  --project=ev-factory-twin \
  --instance=ev-twin-postgres-01
```

The following are **destructive examples**. Inspect the exact resource, export
required evidence, obtain explicit human approval, and run one command at a
time. Never copy this whole section into a terminal.

```bash
gcloud run services delete ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1

gcloud compute instances delete ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a

gcloud sql instances delete ev-twin-postgres-01 \
  --project=ev-factory-twin

gcloud artifacts repositories delete ev-twin \
  --project=ev-factory-twin \
  --location=us-central1
```

Secrets, service accounts, reserved addresses, disks, snapshots, firewall
rules, subnet, and VPC must be inventoried and approved by exact name before
deletion. Never infer their names or delete default/shared networks. After
teardown, rerun the whole-project inventory and inspect Billing reports; hidden
storage, backups, IPs, or images can continue accruing charges.
