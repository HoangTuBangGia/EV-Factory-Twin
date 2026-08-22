# M9 Deployment and End-to-End Acceptance

## Summary

Added the production Backend container, Render Blueprint, container CI smoke,
production configuration fail-fast validation and the hosted edge acceptance
runbook.

## Motivation

The MVP components had separate quality gates but no deployable Render artifact
or one canonical procedure proving the complete Gazebo-to-browser-to-ROS command
round trip.

## Architecture / Contract Impact

Render remains a single FastAPI process because live WebSocket state is
process-local. Production startup now requires PostgreSQL, Supabase Auth, the
edge shared secret, explicit CORS and disabled mock runtime. Supabase migrations
remain a separate controlled deployment step; application startup never mutates
the schema.

## Files Changed

- `apps/backend/Dockerfile`, `.dockerignore`, `render.yaml`
- `.github/workflows/docker.yml`, `Makefile`
- Backend production-settings validation and tests
- ROS launch acceptance stabilization for startup queue updates and slow Gazebo CI
- Deployment, architecture, evaluation and edge-acceptance documentation

## Verification

See the checkpoint handoff for the executed Python, frontend, ROS and container
commands. Hosted acceptance requires team-controlled Render/Vercel/Supabase
credentials and is recorded separately using the runbook.

## CI / Build Impact

Container CI builds the exact uv workspace lock and checks `/health`. Render may
auto-deploy only after GitHub checks pass. No image registry publication or
automatic production migration is introduced.

## Follow-up

Perform the hosted acceptance run and archive its non-secret evidence before the
MVP release tag.
