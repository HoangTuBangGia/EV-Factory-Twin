# GCP Edge Deployment

## Summary

Added reproducible wrappers, systemd units, secure bridge configuration and an
operator runbook for running the ROS 2/Gazebo MVP on one Compute Engine VM.

## Motivation

The local Distrobox flow cannot keep the simulation continuously available for a
hosted demonstration. GCP provides an always-on edge host while preserving the
outbound-only ROS-to-Backend boundary.

## Architecture / Contract Impact

There is no application-contract change. Gazebo, ROS 2 and DDS remain on one
Ubuntu 24.04 edge VM. Only the authenticated bridge connects to Render over
HTTPS. The simulation service never receives the bridge secret.

## Files Changed

- `scripts/edge/*`
- `deploy/gcp/*`
- GCP deployment contract tests
- GCP and MVP acceptance runbooks

## Verification

See the checkpoint handoff for shell syntax, Python gates and ROS verification.
No GCP resource or hosted secret is changed by repository tests.

## CI / Build Impact

The existing Python integration suite validates the deployment contract. VM
provisioning and systemd installation remain explicit human-controlled actions.

## Follow-up

Provision the team-controlled VM, install the accepted commit, connect it to
Render and execute the hosted MVP acceptance runbook.

