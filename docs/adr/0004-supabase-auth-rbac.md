# ADR-0004: Supabase Auth, PostgreSQL RBAC, and split operational duties

## Status

Superseded in part by the two-role MVP decision recorded on 2026-08-22.

## Context

The product requires at least two real user roles and a human-in-the-loop gate
before a simulated scenario can change the realtime factory. The existing UI
label is not authorization, scenarios are process-local, and the WebSocket
currently has no identity handshake.

## Decision

Supabase Auth owns user identity, passwords, access tokens, and session refresh.
The application stores the authoritative business role in
`public.profiles.role`; it never accepts a role selected or sent by the browser.

The role and permission model is:

| Capability | DESIGNER | MONITOR |
|---|---:|---:|
| Read factory, robot, task, KPI, alert, and scenario data | Yes | Yes |
| Run a scenario or edit a layout | Yes | No |
| Submit a simulated scenario | Yes | No |
| Approve, reject, or apply a scenario | No | Yes |
| Control the simulation runtime | No | Yes |
| Read operational audit data when an API is provided | No | Yes |

The MVP has exactly two application roles. User provisioning and role recovery
are operational tasks in Supabase Dashboard, not product features.

FastAPI is the authoritative authorization boundary and returns:

- `401` for a missing, malformed, expired, or unverifiable access token;
- `403` for an inactive user or a verified user without the required role;
- `409` for an invalid scenario state transition.

Next.js middleware refreshes cookie-backed Supabase sessions and protects page
navigation for user experience, while PostgreSQL Row Level Security is a second
line of defence for tables exposed through Supabase. Neither replaces FastAPI
authorization.

The browser authenticates `/ws/factory` by sending this as the first message:

```json
{"type":"auth","access_token":"<Supabase access token>"}
```

The connection is added to the broadcast pool only after token verification and
an active profile lookup. The UI becomes `LIVE` only after `auth.ok`. Invalid
credentials close the socket with `4401`; an inactive user closes it with
`4403`. A reconnect obtains the latest refreshed token and reloads the REST
snapshot.

Supabase's normal access-token lifetime is used (configured as one hour for the
development project) with automatic refresh. A failed refresh clears local
factory state and redirects to `/login?reason=session_expired`. Sessions
otherwise remain active until logout.

## Data policy

The Shared Session Pooler connection string is a backend-only secret. The
frontend receives only the Supabase Project URL and publishable/anon key.
No Supabase service-role key is required by the application runtime.

The target MVP persists profiles, layout versions, scenarios, simulation runs,
commands, alerts, audit events, KPI snapshots, and the telemetry history needed
for monitoring. Telemetry cadence and retention are bounded by the data-retention
policy; the browser never writes these tables directly.

## Consequences

- Designer and Monitor must use separate accounts, which makes the safety gate
  demonstrable and auditable.
- A database connection alone cannot run browser login; deployment also needs
  the public Project URL/key. MVP user creation is performed in Supabase Dashboard.
- PostgreSQL transactions can make a scenario transition and its audit record
  atomic, but cannot be atomic with an in-memory MockFactory reset. The MVP uses
  a guarded transition, an in-process control lock, durable intent audit for
  manual reset/config, and compensating failure handling. Deployment is limited
  to one backend worker; a durable command outbox/single-writer is a later
  production improvement for multi-instance operation.
