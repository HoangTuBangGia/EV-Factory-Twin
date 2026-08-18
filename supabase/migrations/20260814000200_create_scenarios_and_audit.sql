-- Durable scenario workflow and append-only business audit trail.

create type public.scenario_status as enum (
    'DRAFT',
    'SIMULATED',
    'APPROVED',
    'REJECTED',
    'APPLIED'
);

grant usage on type public.scenario_status to authenticated, service_role;

create sequence public.scenario_number_seq as bigint start with 1 increment by 1 cache 1;

create function private.next_scenario_id()
returns text
language plpgsql
volatile
set search_path = ''
as $$
declare
    scenario_number bigint;
    scenario_number_text text;
begin
    scenario_number := nextval('public.scenario_number_seq');
    scenario_number_text := scenario_number::text;
    return 'SCN-' || lpad(
        scenario_number_text,
        greatest(4, char_length(scenario_number_text)),
        '0'
    );
end;
$$;

revoke all on function private.next_scenario_id()
    from public, anon, authenticated, service_role;
grant execute on function private.next_scenario_id() to service_role;

create table public.scenarios (
    id text primary key default private.next_scenario_id(),
    name text not null,
    status public.scenario_status not null default 'SIMULATED',

    -- ScenarioConfig fields from the existing FastAPI contract.
    num_robots smallint not null,
    num_tasks integer not null,
    task_arrival_interval double precision not null,
    travel_time double precision not null,
    loading_time double precision not null,
    simulation_time double precision not null,

    -- ScenarioMetrics fields from the existing FastAPI contract.
    completed_tasks integer not null,
    unfinished_tasks integer not null,
    completion_rate double precision not null,
    throughput_per_hour double precision not null,
    average_cycle_time double precision not null,
    average_waiting_time double precision not null,
    duration_ms double precision not null,

    created_by uuid not null references public.profiles (id) on delete restrict,
    reviewed_by uuid references public.profiles (id) on delete restrict,
    applied_by uuid references public.profiles (id) on delete restrict,
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    applied_at timestamptz,
    updated_at timestamptz not null default now(),
    version integer not null default 1,

    constraint scenarios_name_not_blank
        check (char_length(btrim(name)) between 1 and 80),
    constraint scenarios_num_robots_range check (num_robots between 1 and 10),
    constraint scenarios_num_tasks_range check (num_tasks between 1 and 10000),
    constraint scenarios_task_arrival_interval_range
        check (task_arrival_interval between 1.0 and 60.0),
    constraint scenarios_travel_time_range
        check (travel_time > 0.0 and travel_time <= 86400.0),
    constraint scenarios_loading_time_range
        check (loading_time > 0.0 and loading_time <= 86400.0),
    constraint scenarios_simulation_time_range
        check (simulation_time > 0.0 and simulation_time <= 86400.0),
    constraint scenarios_completed_tasks_nonnegative check (completed_tasks >= 0),
    constraint scenarios_unfinished_tasks_nonnegative check (unfinished_tasks >= 0),
    constraint scenarios_task_totals_match
        check (completed_tasks + unfinished_tasks = num_tasks),
    constraint scenarios_completion_rate_range check (completion_rate between 0.0 and 1.0),
    constraint scenarios_throughput_finite_nonnegative
        check (throughput_per_hour >= 0.0 and throughput_per_hour < 'Infinity'::double precision),
    constraint scenarios_cycle_time_finite_nonnegative
        check (average_cycle_time >= 0.0 and average_cycle_time < 'Infinity'::double precision),
    constraint scenarios_waiting_time_finite_nonnegative
        check (average_waiting_time >= 0.0 and average_waiting_time < 'Infinity'::double precision),
    constraint scenarios_duration_finite_nonnegative
        check (duration_ms >= 0.0 and duration_ms < 'Infinity'::double precision),
    constraint scenarios_version_positive check (version >= 1),
    constraint scenarios_reviewer_separation
        check (reviewed_by is null or reviewed_by <> created_by),
    constraint scenarios_applier_separation
        check (applied_by is null or applied_by <> created_by),
    constraint scenarios_workflow_actor_timestamps check (
        (
            status in ('DRAFT'::public.scenario_status, 'SIMULATED'::public.scenario_status)
            and reviewed_by is null
            and reviewed_at is null
            and applied_by is null
            and applied_at is null
        )
        or (
            status = 'APPROVED'::public.scenario_status
            and reviewed_by is not null
            and reviewed_at is not null
            and applied_by is null
            and applied_at is null
        )
        or (
            status = 'REJECTED'::public.scenario_status
            and reviewed_by is not null
            and reviewed_at is not null
            and applied_by is null
            and applied_at is null
        )
        or (
            status = 'APPLIED'::public.scenario_status
            and reviewed_by is not null
            and reviewed_at is not null
            and applied_by is not null
            and applied_at is not null
            and reviewed_at <= applied_at
        )
    )
);

comment on table public.scenarios is
    'Persisted SimPy benchmark candidates and their human-in-the-loop workflow state.';
comment on column public.scenarios.version is
    'Optimistic-concurrency token. Mutations must match both expected status and version.';
comment on column public.scenarios.id is
    'API-compatible identifier generated as SCN-0001, SCN-0002, and so on.';

create index scenarios_status_created_at_idx
    on public.scenarios (status, created_at desc);
create index scenarios_created_by_created_at_idx
    on public.scenarios (created_by, created_at desc);
create index scenarios_reviewed_by_created_at_idx
    on public.scenarios (reviewed_by, created_at desc)
    where reviewed_by is not null;

create trigger scenarios_set_updated_at
before update on public.scenarios
for each row
execute function private.set_updated_at();

alter table public.scenarios enable row level security;

revoke all on table public.scenarios from anon;
revoke all on table public.scenarios from authenticated;
grant select on table public.scenarios to authenticated;
grant select, insert, update on table public.scenarios to service_role;
grant usage, select on sequence public.scenario_number_seq to service_role;

create policy scenarios_select_active_users
on public.scenarios
for select
to authenticated
using ((select private.is_active_user()));

create table public.audit_events (
    id bigint generated always as identity primary key,
    actor_id uuid not null references public.profiles (id) on delete restrict,
    actor_role public.app_role not null,
    action text not null,
    resource_type text not null,
    resource_id text not null,
    before_data jsonb,
    after_data jsonb,
    request_id uuid not null,
    created_at timestamptz not null default now(),
    constraint audit_events_action_format
        check (action ~ '^[A-Z][A-Z0-9_]{1,79}$'),
    constraint audit_events_resource_type_not_blank
        check (char_length(btrim(resource_type)) between 1 and 80),
    constraint audit_events_resource_id_not_blank
        check (char_length(btrim(resource_id)) between 1 and 200)
);

comment on table public.audit_events is
    'Append-only business audit log. It is distinct from PostgreSQL server logs and pgAudit.';
comment on column public.audit_events.actor_role is
    'Role snapshot at action time so later role changes do not rewrite audit meaning.';
comment on column public.audit_events.request_id is
    'Correlation ID supplied by FastAPI; multiple events from one request may share it.';

create index audit_events_created_at_idx on public.audit_events (created_at desc);
create index audit_events_actor_created_at_idx
    on public.audit_events (actor_id, created_at desc);
create index audit_events_resource_created_at_idx
    on public.audit_events (resource_type, resource_id, created_at desc);
create index audit_events_request_id_idx on public.audit_events (request_id);

-- Derive the role snapshot from the authoritative profile instead of trusting
-- a value supplied by an API client or application caller.
create function private.set_audit_actor_role()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    select role
    into new.actor_role
    from public.profiles
    where id = new.actor_id
      and is_active;

    if new.actor_role is null then
        raise exception 'audit actor must have an active profile'
            using errcode = '23514';
    end if;

    return new;
end;
$$;

revoke all on function private.set_audit_actor_role()
    from public, anon, authenticated, service_role;

create trigger audit_events_set_actor_role
before insert on public.audit_events
for each row
execute function private.set_audit_actor_role();

create function private.reject_audit_event_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception 'audit_events is append-only'
        using errcode = '42501';
end;
$$;

revoke all on function private.reject_audit_event_mutation()
    from public, anon, authenticated, service_role;

create trigger audit_events_reject_update_delete
before update or delete on public.audit_events
for each row
execute function private.reject_audit_event_mutation();

create trigger audit_events_reject_truncate
before truncate on public.audit_events
for each statement
execute function private.reject_audit_event_mutation();

alter table public.audit_events enable row level security;

revoke all on table public.audit_events from anon;
revoke all on table public.audit_events from authenticated;
revoke all on table public.audit_events from service_role;
grant select, insert on table public.audit_events to service_role;
grant usage, select on sequence public.audit_events_id_seq to service_role;
grant select on table public.audit_events to authenticated;

create policy audit_events_select_admin
on public.audit_events
for select
to authenticated
using (
    (select private.is_active_user())
    and (select private.current_app_role()) = 'ADMIN'::public.app_role
);
