# ADR-0005: GCP-native runtime, local JWT auth, and Cloud SQL

## Status

Accepted on 2026-08-24. This supersedes ADR-0003 deployment choices and
ADR-0004 Supabase authentication choices.

## Decision

- Vercel hosts Next.js; Cloud Run hosts FastAPI. Two isolated Vercel projects
  allow the team Render stack and the GCP acceptance stack to coexist.
- Cloud SQL for PostgreSQL 17 is the only application database.
- The existing GCE VM hosts ROS 2 Jazzy, Gazebo Harmonic, and the trusted bridge.
- FastAPI owns authentication and issues HS256 JWT access tokens valid for eight hours.
- Passwords are stored as salted `scrypt` hashes in `public.app_users`.
- Application roles remain exactly `DESIGNER` and `MONITOR`.
- Browser data access remains Browser → FastAPI; PostgreSQL is never exposed to browsers.
- Frontend stores the token in per-tab `sessionStorage`; there is no refresh token.
- Migrations live in `postgres/migrations` and run through `make postgres-migrate`.

## Consequences

Supabase, Render, and Vercel are no longer runtime dependencies. Revocation of
an issued token takes effect at expiry or when the disabled profile is checked
on the next request. Cloud resource provisioning and hosted acceptance follow.
