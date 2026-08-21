# Backend / ROS 2 MVP Contract and Two-Role RBAC

## Summary

Locked the Backend/ROS 2 MVP boundary and reduced application RBAC to Designer
and Monitor. Removed the Admin product extension and added a forward database
migration for existing installations.

## Motivation

The agreed MVP has only two roles and requires telemetry history, command
acknowledgements and bounded deterministic optimization. Existing code and docs
still described an Admin extension and excluded time-series retention.

## Architecture / Contract Impact

- Designer creates/runs/submits; Monitor approves/rejects/applies and controls runtime.
- User provisioning moves to Supabase Dashboard.
- Existing Admin profiles become inactive Designers during migration.
- Monitor is the only role allowed to read audit rows through RLS.
- The canonical Backend/ROS 2 lifecycle, identity and deployment contracts are
  recorded in `docs/backend-ros2-mvp.md`.
- pg_partman remains gated on hosted Supabase capability verification.

## Files Changed

Backend/frontend RBAC, Supabase migration/seed, canonical documentation and tests.
Admin-only API, service, schema, UI and tests were removed.

## Verification

See the checkpoint handoff for executed migration, backend and frontend tests.

## CI / Build Impact

Existing backend, migration and frontend CI commands remain authoritative. No
runtime dependency was added.

## Follow-up

Implement the multi-AMR Gazebo checkpoint using the locked namespace and identity
contract. Verify pg_partman availability before the telemetry-history migration.
