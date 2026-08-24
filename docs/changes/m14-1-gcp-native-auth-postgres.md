# GCP-native Auth and PostgreSQL

## Summary

Replaced Supabase Auth/PostgreSQL with Backend-issued JWT authentication and a
PostgreSQL migration chain for Cloud SQL PostgreSQL 17.

## Motivation

The hosted database has no required production data, and the temporary MVP stack
is moving entirely to GCP through 2026-09-05.

## Architecture / Contract Impact

`POST /api/v1/auth/login` returns the existing bearer-token/current-user contract.
REST and WebSocket bearer semantics remain. Roles are `DESIGNER` and `MONITOR`.
Browser tokens use `sessionStorage`; only FastAPI accesses PostgreSQL.

## Files Changed

Backend auth/config/CLI/tests, Frontend auth/API/tests/config, PostgreSQL migrations,
Makefile, CI, ADR and deployment documentation.

## Verification

- PostgreSQL migration contract: 4 passed.
- Backend/Python gate: Ruff and Mypy clean; 382 passed, 2 PostgreSQL smoke tests skipped.
- Frontend gate: ESLint and TypeScript clean; 104 passed; Next.js production build passed.
- Live PostgreSQL migration/repository smoke remains pending Cloud SQL provisioning.

## CI / Build Impact

CI no longer starts Supabase. The frontend lockfile must be regenerated.

## Follow-up

Provision Cloud SQL, migrate, create two users, deploy Cloud Run, and execute hosted acceptance.
