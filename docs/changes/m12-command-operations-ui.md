# M12 Command Operations UI

## Summary

Added an operator-visible durable command history, attempt details and
Monitor-only retry flow. Command timeout detection now runs in the Backend
lifecycle rather than relying on an API request to trigger expiration.

## Motivation

The apply workflow already persisted commands and emitted realtime updates, but
the browser only showed the most recently created operation. A leased command
could also remain stale until edge or browser traffic invoked expiration.

## Architecture / Contract Impact

- `CommandService` owns a bounded-cadence timeout task started and stopped by
  FastAPI lifespan.
- Unleased attempts expire from their create/retry timestamp; leased attempts
  expire at `lease_expires_at`, so a disconnected edge cannot leave PENDING forever.
- Existing repository expiration remains the single source of timeout state,
  alert, audit and WebSocket behavior.
- `/commands` hydrates REST history and merges `command.updated` by operation ID.
- Both roles can inspect history; only MONITOR can retry eligible operations.
- No API schema or database migration changed.

## Files Changed

- Backend settings, command lifecycle and focused timeout regression test.
- Frontend command page, store snapshot action, navigation and RBAC tests.
- Backend environment example and canonical documentation.

## Verification

Run `make check`, `make frontend-check` and `make postgres-smoke` with
`TEST_DATABASE_URL` pointing to migrated local Supabase.

## CI / Build Impact

Existing Backend and Frontend Makefile quality gates cover the new worker and UI.
No new dependency or service is required.

## Follow-up

M13 removes mock robot registry assumptions in ROS mode and closes the hosted
Backend-to-GCP edge acceptance path.
