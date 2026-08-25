# GCP Compute Engine Edge Runbook

## Scope

Run the ROS 2 Jazzy, Gazebo Harmonic, fleet/task managers and authenticated
telemetry bridge on Ubuntu 24.04 Compute Engine. Vercel, Cloud Run and Cloud SQL
provide the application services. Develop and production use separate edge VMs.
ROS DDS and Gazebo are never exposed to the Internet.

Each environment uses one ordinary VM and headless Gazebo. Kubernetes, GPU,
Spot VM and multi-VM DDS are deliberately excluded.

## 1. Provisioning contract

Create a dedicated-project or dedicated-VPC Ubuntu 24.04 VM with:

- at least 4 vCPU, 16 GB RAM and 50 GB persistent disk for the initial load test;
- standard on-demand lifecycle, automatic restart and deletion protection;
- outbound TCP 443 to Cloud Run and package repositories;
- no inbound ROS/Gazebo ports;
- SSH restricted to Identity-Aware Proxy or another team-controlled admin path;
- time synchronization enabled.

Production has no external address and uses Cloud NAT for outbound traffic.
Develop may retain its existing ephemeral address during migration. A static
public IP is not required by the application.

Do not grant broad cloud API roles to the VM service account. The current runtime
does not call GCP APIs.

## 2. Install prerequisites

Follow the official ROS 2 Jazzy Ubuntu 24.04 and Gazebo Harmonic installation
instructions. Install `git`, `rosdep`, `colcon`, the package dependencies declared
under `ros2_ws/src`, and the `ament_python` colcon extension. Do not install
project Python dependencies with pip.

For the production VM, run the repository bootstrap from the operator machine:

```bash
make gcp-production-edge-bootstrap
```

The target connects through IAP and runs `scripts/gcp_edge_bootstrap.sh` as
root. It is safe to rerun and does not clone application code, read secrets, or
start runtime services.

Create a locked-down runtime account and checkout directory:

```bash
sudo useradd --create-home --shell /bin/bash ev-twin
sudo install -d -o ev-twin -g ev-twin /opt/ev-factory-twin
```

Clone or copy the exact accepted commit into `/opt/ev-factory-twin`, owned by
`ev-twin`. Then build as that user:

```bash
cd /opt/ev-factory-twin
source /opt/ros/jazzy/setup.bash
make ros-check
```

Do not run the services from a floating branch. Record the deployed commit SHA.

## 3. Configure the bridge secret

Create the configuration directory and copy the template:

```bash
sudo install -d -o root -g root -m 0700 /etc/ev-factory-twin
sudo install -o root -g root -m 0600 \
  deploy/gcp/bridge.env.example /etc/ev-factory-twin/bridge.env
sudoedit /etc/ev-factory-twin/bridge.env
```

Set the environment's Cloud Run HTTPS URL and matching edge secret. Keep the
file `root:root` mode `0600`; systemd reads it before dropping to the `ev-twin`
service user. Do not put the secret in instance metadata, startup scripts,
repository files, command arguments or logs.

Secret Manager may be used as the operator's source of truth, but materialize the
secret into this root-only file during an approved maintenance action. The
runtime intentionally has no dependency on the `gcloud` CLI or cloud API roles.

## 4. Install and start systemd services

```bash
sudo install -o root -g root -m 0644 \
  deploy/gcp/systemd/ev-twin-simulation.service /etc/systemd/system/
sudo install -o root -g root -m 0644 \
  deploy/gcp/systemd/ev-twin-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ev-twin-simulation.service
sudo systemctl enable --now ev-twin-bridge.service
```

The simulation runs `gz sim -s -r` through the ROS launch file. The bridge waits
for network-online and the simulation unit, validates HTTPS/secret configuration,
then connects outbound to Cloud Run. Both units restart only after failure and use
SIGINT for ROS-aware shutdown.

## 5. Verify and operate

```bash
systemctl status ev-twin-simulation.service ev-twin-bridge.service
journalctl -u ev-twin-simulation.service -u ev-twin-bridge.service --since today
sudo -u ev-twin bash -lc \
  'source /opt/ros/jazzy/setup.bash && source /opt/ev-factory-twin/ros2_ws/install/setup.bash && ros2 node list'
```

Expected nodes include both namespaced AMRs, Fleet Manager and Task Manager.
The Backend must show the environment-specific bridge connected and telemetry for `AMR-01` and
`AMR-02`. Continue with `docs/runbooks/mvp-edge-acceptance.md`.

Use journald retention/forwarding appropriate for the project, but never log the
environment file. Monitor CPU, memory, disk, VM uptime, service restart count,
bridge disconnect alerts and ROS-to-Backend latency before resizing the VM.

## 6. Deploy an update

Stop services, update to an explicitly accepted commit, rebuild, run
`make ros-check`, and only then restart:

```bash
sudo systemctl stop ev-twin-bridge.service ev-twin-simulation.service
sudo -u ev-twin git -C /opt/ev-factory-twin fetch --prune
sudo -u ev-twin git -C /opt/ev-factory-twin checkout --detach ACCEPTED_COMMIT_SHA
sudo -u ev-twin bash -lc \
  'cd /opt/ev-factory-twin && source /opt/ros/jazzy/setup.bash && make ros-check'
sudo systemctl start ev-twin-simulation.service ev-twin-bridge.service
```

The human owns the accepted SHA and Git operation. Roll back by repeating the
same sequence with the previous accepted SHA. Configuration changes require an
approved edit of `/etc/ev-factory-twin/bridge.env` followed by bridge restart.

## 7. Failure handling

- Bridge restart loop: validate Render URL, secret length, DNS and outbound 443.
- Render reports disconnect: inspect bridge journal and VM clock before retrying.
- Gazebo CPU saturation: confirm headless `-s -r`, then resize the VM based on
  measured load; do not add a GPU without evidence.
- ROS nodes missing: source both setup files and inspect the simulation journal.
- Command timeout: keep the `operation_id`, restore the edge, then use the
  Backend retry endpoint to create the next immutable attempt.
