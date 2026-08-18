# ADR-0004: Supabase Auth, PostgreSQL RBAC, and split operational duties

## Status

Accepted for the authentication MVP.

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

| Capability | DESIGNER | MONITOR | ADMIN |
|---|---:|---:|---:|
| Read factory, robot, task, KPI, alert, and scenario data | Yes | Yes | Yes |
| Run a scenario or edit a future layout | Yes | No | No |
| Approve, reject, or apply a scenario | No | Yes | No |
| Start, stop, reset, or configure MockFactory | No | Yes | No |
| Manage users/roles and read business audit records | No | No | Yes |

`ADMIN` is a technical role, not a third operational persona. It does not
inherit Designer or Monitor mutations. Public sign-up is disabled for the MVP;
accounts are invited or created by an administrator.

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
`SUPABASE_SERVICE_ROLE_KEY`, when the Admin API is implemented, also remains
server-only.

The MVP persists profiles, scenarios, review/apply actors, business audit
events, and coarse KPI snapshots. It does not persist raw 10 Hz robot telemetry
and does not enable TimescaleDB. KPI snapshots use a ten-second cadence until
measurement justifies a dedicated time-series database.

## Consequences

- Designer and Monitor must use separate accounts, which makes the safety gate
  demonstrable and auditable.
- A database connection alone cannot run browser login; deployment also needs
  the public Project URL/key. Programmatic Auth user creation needs a server-only
  service-role key or must be done in the Supabase Dashboard.
- PostgreSQL transactions can make a scenario transition and its audit record
  atomic, but cannot be atomic with an in-memory MockFactory reset. The MVP uses
  a guarded transition, an in-process control lock, durable intent audit for
  manual reset/config, and compensating failure handling. Deployment is limited
  to one backend worker; a durable command outbox/single-writer is a later
  production improvement for multi-instance operation.
