-- Reduce the application contract to the two agreed MVP roles.
-- Existing ADMIN profiles are disabled and mapped to DESIGNER (least privilege).

drop policy profiles_select_own_or_admin on public.profiles;
drop policy audit_events_select_admin on public.audit_events;

drop trigger ev_twin_on_auth_user_created on auth.users;
drop function private.handle_new_auth_user();
drop function private.current_app_role();

update public.profiles
set is_active = false
where role = 'ADMIN'::public.app_role;

update auth.users
set raw_app_meta_data = jsonb_set(
        coalesce(raw_app_meta_data, '{}'::jsonb),
        '{app_role}',
        '"DESIGNER"'::jsonb
    ),
    updated_at = now()
where upper(coalesce(raw_app_meta_data ->> 'app_role', '')) = 'ADMIN';

alter type public.app_role rename to app_role_legacy;
create type public.app_role as enum ('DESIGNER', 'MONITOR');
grant usage on type public.app_role to authenticated, service_role;

alter table public.profiles
    alter column role type public.app_role
    using (
        case
            when role::text = 'MONITOR' then 'MONITOR'
            else 'DESIGNER'
        end
    )::public.app_role;

alter table public.audit_events
    alter column actor_role type public.app_role
    using (
        case
            when actor_role::text = 'MONITOR' then 'MONITOR'
            else 'DESIGNER'
        end
    )::public.app_role;

drop type public.app_role_legacy;

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
    activate_profile := requested_role_text in ('DESIGNER', 'MONITOR');
    requested_role := case requested_role_text
        when 'MONITOR' then 'MONITOR'::public.app_role
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

revoke all on function private.handle_new_auth_user()
    from public, anon, authenticated, service_role;

create trigger ev_twin_on_auth_user_created
after insert on auth.users
for each row
execute function private.handle_new_auth_user();

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

revoke all on function private.current_app_role()
    from public, anon, authenticated, service_role;
grant execute on function private.current_app_role() to authenticated, service_role;

create policy profiles_select_own
on public.profiles
for select
to authenticated
using (
    (select private.is_active_user())
    and id = (select auth.uid())
);

create policy audit_events_select_monitor
on public.audit_events
for select
to authenticated
using (
    (select private.is_active_user())
    and (select private.current_app_role()) = 'MONITOR'::public.app_role
);
