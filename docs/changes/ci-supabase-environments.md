# CI and Supabase Environments

## Summary

Hosted browser E2E now covers only the MVP roles `DESIGNER` and `MONITOR`.
Local development uses Supabase CLI defaults, while Render/Vercel use hosted
Supabase environment values.

## Motivation

The MVP requires two operational roles. Requiring Admin credentials made the
hosted E2E gate depend on an optional extension. Local and hosted database values
also needed an explicit, repeatable separation.

## Architecture / Contract Impact

- No runtime API or database contract changes.
- Admin functionality remains in the codebase but is not an MVP E2E prerequisite.
- Local Supabase provides PostgreSQL and Auth for development.
- Hosted Supabase remains the staging/production database and Auth provider.

## Files Changed

- `.github/workflows/ci.yml`
- `Makefile`
- `apps/backend/.env.example`
- `apps/frontend/.env.example`
- `apps/frontend/e2e/hosted-rbac.spec.ts`
- `docs/development.md`
- `supabase/README.md`

## Verification

- `git diff --check`
- `make -n supabase-start supabase-status supabase-reset supabase-stop`
- `npm run test:e2e:list`
- `npm test -- --run`

## CI / Build Impact

The hosted E2E job now requires seven secrets: database URL, Supabase URL,
publishable key, and email/password pairs for Designer and Monitor. Backend,
frontend, migration and ROS CI jobs are unchanged.

## Follow-up

Add a post-deployment smoke check after stable Vercel and Render production URLs
and deployment manifests exist.
