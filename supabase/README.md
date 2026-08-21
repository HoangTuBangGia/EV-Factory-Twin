# Supabase database workflow

The ordered SQL files in `migrations/` define the Factory Twin application
schema. Supabase Auth owns credentials; these migrations never store passwords.
`config.toml` contains local, non-secret defaults and disables public signup in
the local stack. Its `project_id` is a local stack name, not a hosted project
reference. Its PostgreSQL major version is pinned to the hosted development
project's verified major version so local migration behavior stays aligned.

## Apply to the development project

Use the Supabase CLI from the repository root:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push --dry-run
supabase db push
```

`supabase link` prompts for the database password. Do not put that password or a
connection URL in a command, migration, committed config file, screenshot, or
CI log. Migration history makes these one-time files run in timestamp order.

For a fully local Supabase stack, use:

```bash
make supabase-start
make supabase-status
make supabase-reset
```

`make supabase-reset` is destructive to the local database but replays the
complete migration chain. Use `make supabase-stop` when finished. Never run a
linked reset against staging or production.

## Offline CI checks

Run the migration gate without a database or Supabase credentials:

```bash
make migration-check
```

The gate parses every migration with PostgreSQL's parser and checks the expected
tables, columns, enums, RLS enablement, grants, policy predicates, protected
`SECURITY DEFINER` functions, and the append-only audit contract. CI runs this
gate explicitly before typechecking and the full test suite.

This static gate cannot prove runtime RLS behavior for real JWT claims. Before a
release, also replay the migrations against local/hosted Supabase and test the
policies with access tokens for Designer, Monitor, an inactive user, and
an anonymous request.

## Disable public sign-up

In the Supabase Dashboard, open **Authentication > Providers > Email** and turn
off the option that allows new users to sign up. Keep email/password sign-in
enabled. Factory Twin accounts are created by an administrator only.

## Bootstrap the two demo accounts

1. Open **Authentication > Users** in the Supabase Dashboard.
2. Choose **Add user > Create new user**.
3. Create one Designer and one Monitor email/password account. Use
   **Auto Confirm User** for demo accounts if email confirmation is not part of
   the demo.
4. Do not reuse the database password as a user password, and do not commit the
   two passwords anywhere.
5. Users created in the Dashboard have no trusted `app_role` metadata, so the
   safety trigger creates them as inactive Designers. Open **SQL Editor** and
   assign the intended roles explicitly, replacing the example emails:

```sql
update public.profiles as profiles
set display_name = 'Demo Designer', role = 'DESIGNER', is_active = true
from auth.users as users
where profiles.id = users.id
  and lower(users.email) = lower('designer@example.com');

update public.profiles as profiles
set display_name = 'Demo Monitor', role = 'MONITOR', is_active = true
from auth.users as users
where profiles.id = users.id
  and lower(users.email) = lower('monitor@example.com');

```

Verify that there is exactly one active account for each role:

```sql
select users.email, profiles.display_name, profiles.role, profiles.is_active
from public.profiles as profiles
join auth.users as users on users.id = profiles.id
order by profiles.role, users.email;
```

The product does not expose user-management endpoints. Provisioning and recovery
remain controlled through Supabase Dashboard for the MVP.

## Runtime write rules

- Browser clients may only read rows allowed by RLS.
- FastAPI performs all scenario, audit, and KPI writes after its own JWT and
  role checks.
- Approve/reject/apply must use a conditional update on both expected `status`
  and `version`; increment `version` in the same statement and treat zero
  updated rows as a conflict.
- Insert the scenario transition and its `audit_events` row in one transaction.
- The audit insert trigger derives `actor_role` from the active profile; callers
  must not treat an incoming role value as authoritative.
- Store a KPI snapshot at most once every 10 seconds of wall time. Do not store
  the realtime robot telemetry stream in PostgreSQL for this MVP.

## Rollback

Supabase migrations are forward-only. For a shared database, create and review
a new compensating migration; do not edit a migration that has already run and
do not run a linked database reset.

For an unused development project where data loss is explicitly acceptable,
drop objects in reverse dependency order: `kpi_snapshots`, audit triggers and
`audit_events`, `scenarios` and its sequence/type, the `auth.users` trigger,
private helper functions, `profiles`, and finally `app_role`. Take a backup
first. Never use `supabase db reset --linked` against staging or production.
