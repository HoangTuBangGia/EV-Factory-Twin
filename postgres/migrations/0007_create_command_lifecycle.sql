-- Durable human-approved scenario application and edge command delivery.

create type public.command_status as enum (
    'PENDING', 'ACKNOWLEDGED', 'COMPLETED', 'FAILED', 'TIMED_OUT'
);
create table public.scenario_reviews (
    id bigint generated always as identity primary key,
    scenario_id text not null references public.scenarios (id) on delete restrict,
    decision public.scenario_status not null,
    actor_id uuid not null references public.profiles (id) on delete restrict,
    created_at timestamptz not null default now(),
    constraint scenario_reviews_decision_check
        check (decision in ('SUBMITTED', 'APPROVED', 'REJECTED'))
);

create table public.commands (
    operation_id uuid primary key,
    scenario_id text not null references public.scenarios (id) on delete restrict,
    status public.command_status not null default 'PENDING',
    payload jsonb not null,
    timeout_seconds double precision not null,
    max_retries smallint not null,
    requested_by uuid not null references public.profiles (id) on delete restrict,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint commands_payload_object check (jsonb_typeof(payload) = 'object'),
    constraint commands_timeout_range check (timeout_seconds > 0 and timeout_seconds <= 300),
    constraint commands_retry_range check (max_retries between 0 and 5)
);

create table public.command_attempts (
    operation_id uuid not null references public.commands (operation_id) on delete restrict,
    attempt_number smallint not null,
    status public.command_status not null default 'PENDING',
    leased_by text,
    leased_at timestamptz,
    lease_expires_at timestamptz,
    acknowledged_at timestamptz,
    completed_at timestamptz,
    detail text not null default '',
    primary key (operation_id, attempt_number),
    constraint command_attempts_number_positive check (attempt_number >= 1),
    constraint command_attempts_lease_pair check (
        (leased_by is null and leased_at is null and lease_expires_at is null)
        or (leased_by is not null and leased_at is not null and lease_expires_at > leased_at)
    )
);

create table public.command_acknowledgements (
    id bigint generated always as identity primary key,
    operation_id uuid not null,
    attempt_number smallint not null,
    status public.command_status not null,
    bridge_id text not null,
    detail text not null default '',
    created_at timestamptz not null default now(),
    foreign key (operation_id, attempt_number)
        references public.command_attempts (operation_id, attempt_number) on delete restrict,
    constraint command_ack_bridge_not_blank check (char_length(btrim(bridge_id)) between 1 and 100)
);
alter table public.command_acknowledgements
    add constraint command_ack_idempotency unique (operation_id, attempt_number, status);

create function private.record_scenario_review()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if new.status is distinct from old.status
       and new.status in ('SUBMITTED', 'APPROVED', 'REJECTED') then
        insert into public.scenario_reviews (scenario_id, decision, actor_id, created_at)
        values (
            new.id,
            new.status,
            case when new.status = 'SUBMITTED' then new.created_by else new.reviewed_by end,
            coalesce(new.reviewed_at, now())
        );
    end if;
    return new;
end;
$$;
revoke all on function private.record_scenario_review() from public;
create trigger scenarios_record_review after update of status on public.scenarios
for each row execute function private.record_scenario_review();

create index scenario_reviews_scenario_created_idx
    on public.scenario_reviews (scenario_id, created_at);
create index commands_status_created_idx on public.commands (status, created_at);
create unique index commands_one_active_per_scenario_idx on public.commands (scenario_id)
    where status in ('PENDING', 'ACKNOWLEDGED');
create index command_attempts_lease_idx on public.command_attempts (status, lease_expires_at);
create index command_ack_operation_idx
    on public.command_acknowledgements (operation_id, attempt_number, created_at);

create trigger commands_set_updated_at before update on public.commands
for each row execute function private.set_updated_at();

-- Replace the pre-M7 projection constraint with the submitted lifecycle.
alter table public.scenarios drop constraint scenarios_workflow_actor_timestamps;
alter table public.scenarios add constraint scenarios_workflow_actor_timestamps check (
    (status in ('DRAFT', 'SIMULATED', 'SUBMITTED') and reviewed_by is null and applied_by is null)
    or (status in ('APPROVED', 'REJECTED') and reviewed_by is not null and reviewed_at is not null
        and applied_by is null and applied_at is null)
    or (status = 'APPLIED' and reviewed_by is not null and reviewed_at is not null
        and applied_by is not null and applied_at is not null and reviewed_at <= applied_at)
);
