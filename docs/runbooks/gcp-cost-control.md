# GCP Cost Control Runbook

## Scope

This runbook inventories the billable resources created for the GCP-native MVP
in project `ev-factory-twin`. Use it to monitor costs during acceptance and to
remove the temporary stack before 2026-09-05.

Never paste database passwords, JWT secrets, edge shared secrets, or service
account credentials into tickets, screenshots, shell history, or this document.

## Cost priority

Review resources in this order:

1. Compute Engine VM `ev-twin-edge-01` while running.
2. Cloud SQL instance `ev-twin-postgres-01` while running.
3. Compute Engine persistent disks, including while their VM is stopped.
4. Cloud SQL storage, backups, and public IPv4 allocation.
5. Network egress and any external IPv4 or Cloud NAT resources.
6. Cloud Run request/CPU/memory usage.
7. Artifact Registry image storage, Cloud Build, and Secret Manager usage.

Google Cloud pricing can change. Use the Billing reports and the official
pricing pages rather than treating estimates in project discussions as an
invoice.

## Billing controls

- [Billing overview](https://console.cloud.google.com/billing?project=ev-factory-twin)
- [Billing reports](https://console.cloud.google.com/billing/reports?project=ev-factory-twin)
- [Cost table](https://console.cloud.google.com/billing/costs?project=ev-factory-twin)
- [Budgets and alerts](https://console.cloud.google.com/billing/budgets?project=ev-factory-twin)

Create a temporary-project budget appropriate to the remaining credit and send
alerts at 50%, 80%, and 100%. A budget alerts operators but does not
automatically stop resources.

## Compute Engine edge

Current resource:

- instance: `ev-twin-edge-01`
- zone: `us-central1-a`
- machine type: `e2-standard-4` (4 vCPU, 16 GB RAM)
- boot disk: approximately 50 GB
- workload: headless Gazebo Harmonic, ROS 2 Jazzy, fleet/task managers, and the
  telemetry bridge

Console:

- [VM instance](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/ev-twin-edge-01?project=ev-factory-twin)
- [All VM instances](https://console.cloud.google.com/compute/instances?project=ev-factory-twin)
- [Persistent disks](https://console.cloud.google.com/compute/disks?project=ev-factory-twin)
- [External IP addresses](https://console.cloud.google.com/networking/addresses/list?project=ev-factory-twin)

Inspect the instance without changing it:

```bash
gcloud compute instances list \
  --project=ev-factory-twin \
  --format='table(name,zone.basename(),machineType.basename(),status,disks[0].diskSizeGb,networkInterfaces[0].accessConfigs[0].natIP)'
```

While the VM runs, CPU, memory, disk, external IPv4, and egress charges can
apply. Stopping it ends CPU and memory charges, but attached persistent disks
remain billable. An ephemeral external address is normally released when the VM
stops; reserved static addresses require separate review.

Stop the VM when ROS acceptance is not running:

```bash
gcloud compute instances stop ev-twin-edge-01 \
  --project=ev-factory-twin \
  --zone=us-central1-a
```

Stopping is reversible and preserves the boot disk. It interrupts Gazebo, ROS,
telemetry, and command acknowledgement until the VM is started again.

## Cloud SQL PostgreSQL

Current resource:

- instance: `ev-twin-postgres-01`
- region: `us-central1`
- database engine: PostgreSQL 17
- machine tier: `db-f1-micro`
- consumer: Cloud Run service `ev-twin-api` through the Cloud SQL connector

Console:

- [Cloud SQL instance](https://console.cloud.google.com/sql/instances/ev-twin-postgres-01/overview?project=ev-factory-twin)
- [All Cloud SQL instances](https://console.cloud.google.com/sql/instances?project=ev-factory-twin)

Inspect the instance:

```bash
gcloud sql instances describe ev-twin-postgres-01 \
  --project=ev-factory-twin \
  --format='yaml(name,state,region,databaseVersion,settings.tier,settings.dataDiskSizeGb,settings.dataDiskType,settings.backupConfiguration,ipAddresses)'
```

The database instance, provisioned storage, backup storage, public IPv4, and
network egress can be billed separately. Cloud SQL storage remains billable
while the instance is stopped. Stopping Cloud SQL also makes login, API
persistence, telemetry history, scenarios, and commands unavailable.

See the current [Cloud SQL pricing](https://cloud.google.com/sql/pricing).

## Cloud Run Backend

Current resource:

- service: `ev-twin-api`
- region: `us-central1`
- CPU: 1
- memory: 512 MiB
- minimum instances: 0
- maximum instances: 1

Console:

- [Cloud Run service](https://console.cloud.google.com/run/detail/us-central1/ev-twin-api/metrics?project=ev-factory-twin)
- [All Cloud Run services](https://console.cloud.google.com/run?project=ev-factory-twin)

Inspect the effective revision and scaling configuration:

```bash
gcloud run services describe ev-twin-api \
  --project=ev-factory-twin \
  --region=us-central1 \
  --format='yaml(status.url,status.latestReadyRevisionName,spec.template.metadata.annotations,spec.template.spec.containerConcurrency,spec.template.spec.containers[0].resources)'
```

With `min-instances=0`, the service can scale to zero. Requests, CPU, memory,
and egress can still incur usage-based charges. `max-instances=1` is also an MVP
runtime invariant because authoritative realtime state is held by one Backend
worker.

## Artifact Registry and Cloud Build

Current Artifact Registry repository:

- repository: `ev-twin`
- location: `us-central1`
- content: immutable Backend container images

Console:

- [Artifact Registry](https://console.cloud.google.com/artifacts?project=ev-factory-twin)
- [Cloud Build history](https://console.cloud.google.com/cloud-build/builds?project=ev-factory-twin)

Inspect repositories and images:

```bash
gcloud artifacts repositories list \
  --project=ev-factory-twin \
  --location=us-central1

gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/ev-factory-twin/ev-twin \
  --include-tags
```

Inspect recent builds:

```bash
gcloud builds list \
  --project=ev-factory-twin \
  --limit=20 \
  --format='table(id,status,createTime,duration,images)'
```

Artifact Registry charges for retained storage. Cloud Build is usage-based and
does not run continuously. Keep the currently deployed image and any explicitly
required rollback image; review older images before deletion.

## Secret Manager

Known secrets:

- `ev-twin-database-url`
- `ev-twin-auth-jwt-secret`
- `ev-twin-edge-telemetry-secret`

Console:

- [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=ev-factory-twin)

List metadata without reading secret values:

```bash
gcloud secrets list \
  --project=ev-factory-twin \
  --format='table(name,createTime)'
```

Secret versions and access operations can incur small usage-based charges. Do
not inspect secret payloads merely to audit cost.

## Networking

The edge deployment uses a VPC, subnet, firewall rules, and IAP-restricted SSH.
VPC definitions and firewall rules are not expected to be primary cost drivers,
but external IPv4 addresses, Cloud NAT, and network egress require review.

Console:

- [VPC networks](https://console.cloud.google.com/networking/networks/list?project=ev-factory-twin)
- [Firewall policies and rules](https://console.cloud.google.com/net-security/firewall-manager/firewall-policies/list?project=ev-factory-twin)
- [External IP addresses](https://console.cloud.google.com/networking/addresses/list?project=ev-factory-twin)
- [Cloud NAT](https://console.cloud.google.com/net-services/nat/list?project=ev-factory-twin)

Inventory networking resources:

```bash
gcloud compute networks list --project=ev-factory-twin
gcloud compute networks subnets list --project=ev-factory-twin
gcloud compute firewall-rules list --project=ev-factory-twin
gcloud compute addresses list --project=ev-factory-twin
gcloud compute routers list --project=ev-factory-twin
```

The GCE bridge requires outbound HTTPS only. ROS DDS and Gazebo ports must not
be exposed publicly.

## Daily check during acceptance

1. Open Billing reports and filter by project and service.
2. Confirm whether `ev-twin-edge-01` needs to remain running.
3. Check Cloud SQL storage and backup growth.
4. Check Cloud Run request count and revision count.
5. Review Artifact Registry image growth after builds.
6. Confirm there is no unused static IP, Cloud NAT, snapshot, or disk.
7. Keep ROS logs and persistent-disk utilization below operational thresholds.

## Teardown before 2026-09-05

Before deleting anything, export the required audit evidence, scenario results,
database backup, deployed Git SHA, Cloud Run revision, and acceptance logs.

Deletion is destructive and must be reviewed and approved resource by resource.
The final teardown should account for:

- Cloud Run service `ev-twin-api`;
- Cloud SQL instance `ev-twin-postgres-01`, its backups, and retained exports;
- GCE VM `ev-twin-edge-01` and its boot disk;
- unused snapshots, images, external IP addresses, and Cloud NAT resources;
- Artifact Registry repository or unneeded images;
- GCP secrets and service accounts created only for this stack;
- the temporary Vercel GCP project;
- billing reports after deletion to confirm charges stop.

Stopping a VM or database is not equivalent to deleting its storage. Verify the
Billing cost table after teardown instead of assuming that an empty application
page means billing has stopped.
