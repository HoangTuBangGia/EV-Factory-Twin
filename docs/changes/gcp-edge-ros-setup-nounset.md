# GCP Edge ROS Setup Nounset Fix

## Summary

Made the GCP edge wrappers source ROS and workspace setup files before enabling
Bash nounset mode.

## Motivation

The production Ubuntu ROS setup script reads `AMENT_TRACE_SETUP_FILES` before it
is guaranteed to be defined. Starting either systemd service with `set -u`
already active therefore caused an immediate restart loop.

## Architecture / Contract Impact

There is no API or runtime contract change. The wrappers retain errexit and
pipefail throughout startup, then restore nounset immediately after the two
third-party environment scripts have been sourced.

## Files Changed

- Simulation and telemetry bridge edge wrappers.
- GCP deployment regression test.

## Verification

Run the focused GCP deployment test and `make ros-check`, then update the GCP VM
to the accepted commit before restarting its systemd services.

## CI / Build Impact

Existing Backend integration and ROS workflows cover the change. No dependency,
migration or infrastructure resource is added.

## Follow-up

Resume the hosted Render-to-GCP acceptance run and record service, registry,
telemetry and command evidence.
