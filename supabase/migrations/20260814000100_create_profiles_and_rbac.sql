-- Factory Twin authentication profile and application-role foundation.
--
-- Supabase Auth remains the only owner of passwords and login identities.
-- public.profiles stores application authorization data only.

create type public.app_role as enum ('DESIGNER', 'MONITOR', 'ADMIN');

grant usage on type public.app_role to authenticated, service_role;

create table public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text not null,
    role public.app_role not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint profiles_display_name_not_blank
        check (char_length(btrim(display_name)) between 1 and 120)
);

comment on table public.profiles is
    'Application profile and authoritative Factory Twin role for a Supabase Auth user.';
comment on column public.profiles.role is
    'Business authorization source. Never accept this value from a login form or user_metadata.';

create index profiles_role_active_idx on public.profiles (role, is_active);

create schema if not exists private;

revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated, service_role;

create function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

revoke all on function private.set_updated_at() from public, anon, authenticated, service_role;

create trigger profiles_set_updated_at
before update on public.profiles
for each row
execute function private.set_updated_at();

-- raw_app_meta_data is controlled by trusted Auth Admin operations. A user
-- created without an explicit valid role is provisioned as an inactive
-- DESIGNER, which is the safest operational fallback: it cannot approve,
-- apply, or control the factory. An admin must activate that profile.
create function private.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    requested_role_text text := upper(coalesce(new.raw_app_meta_data ->> 'app_role', ''));
    requested_role public.app_role;
    activate_profile boolean;
    profile_name text;
begin
    activate_profile := requested_role_text in ('DESIGNER', 'MONITOR', 'ADMIN');
    requested_role := case requested_role_text
        when 'MONITOR' then 'MONITOR'::public.app_role
        when 'ADMIN' then 'ADMIN'::public.app_role
        else 'DESIGNER'::public.app_role
    end;

    profile_name := left(
        coalesce(
            nullif(btrim(new.raw_user_meta_data ->> 'display_name'), ''),
            nullif(split_part(coalesce(new.email, ''), '@', 1), ''),
            'Factory Twin user'
        ),
        120
    );

    insert into public.profiles (id, display_name, role, is_active)
    values (new.id, profile_name, requested_role, activate_profile);

    return new;
end;
$$;

revoke all on function private.handle_new_auth_user() from public, anon, authenticated, service_role;

create trigger ev_twin_on_auth_user_created
after insert on auth.users
for each row
execute function private.handle_new_auth_user();

-- Backfill users that existed before this migration. Users without trusted
-- app metadata remain inactive until an administrator assigns a role.
insert into public.profiles (id, display_name, role, is_active, created_at, updated_at)
select
    users.id,
    left(
        coalesce(
            nullif(btrim(users.raw_user_meta_data ->> 'display_name'), ''),
            nullif(split_part(coalesce(users.email, ''), '@', 1), ''),
            'Factory Twin user'
        ),
        120
    ),
    case upper(coalesce(users.raw_app_meta_data ->> 'app_role', ''))
        when 'MONITOR' then 'MONITOR'::public.app_role
        when 'ADMIN' then 'ADMIN'::public.app_role
        else 'DESIGNER'::public.app_role
    end,
    upper(coalesce(users.raw_app_meta_data ->> 'app_role', ''))
        in ('DESIGNER', 'MONITOR', 'ADMIN'),
    coalesce(users.created_at, now()),
    now()
from auth.users as users
on conflict (id) do nothing;

-- These helpers execute as their owner so policies can inspect the caller's
-- profile without recursively invoking profiles RLS. They live in a schema
-- that is not exposed through the Data API.
create function private.is_active_user()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.profiles
        where id = (select auth.uid())
          and is_active
    );
$$;

create function private.current_app_role()
returns public.app_role
language sql
stable
security definer
set search_path = ''
as $$
    select role
    from public.profiles
    where id = (select auth.uid())
      and is_active;
$$;

revoke all on function private.is_active_user() from public, anon, authenticated, service_role;
revoke all on function private.current_app_role() from public, anon, authenticated, service_role;
grant execute on function private.is_active_user() to authenticated, service_role;
grant execute on function private.current_app_role() to authenticated, service_role;

alter table public.profiles enable row level security;

revoke all on table public.profiles from anon;
revoke all on table public.profiles from authenticated;
grant select on table public.profiles to authenticated;
grant select, insert, update, delete on table public.profiles to service_role;

create policy profiles_select_own_or_admin
on public.profiles
for select
to authenticated
using (
    (select private.is_active_user())
    and (
        id = (select auth.uid())
        or (select private.current_app_role()) = 'ADMIN'::public.app_role
    )
);

