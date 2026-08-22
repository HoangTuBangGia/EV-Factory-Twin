-- Runtime health, alert lifecycle and bounded operational history.

create schema if not exists partman;
create extension if not exists pg_partman with schema partman;
create extension if not exists pg_cron;

create type public.alert_severity as enum ('INFO', 'WARNING', 'CRITICAL');
create type public.alert_status as enum ('ACTIVE', 'CLEARED');
grant usage on type public.alert_severity, public.alert_status to authenticated, service_role;

create table public.robot_telemetry_history (
    robot_id text not null,
    source_timestamp timestamptz not null,
    ingested_at timestamptz not null default now(),
    pose jsonb not null,
    velocity jsonb not null,
    battery double precision not null,
    status text not null,
    task_id text,
    payload_id text,
    ordering_status text not null,
    primary key (robot_id, source_timestamp),
    constraint telemetry_robot_id_not_blank check (char_length(btrim(robot_id)) between 1 and 100),
    constraint telemetry_pose_object check (jsonb_typeof(pose) = 'object'),
    constraint telemetry_velocity_object check (jsonb_typeof(velocity) = 'object'),
    constraint telemetry_battery_range check (battery between 0.0 and 100.0),
    constraint telemetry_ordering_status check (ordering_status in ('ACCEPTED', 'LATE'))
) partition by range (source_timestamp);

comment on table public.robot_telemetry_history is
    'Sampled ROS telemetry history. Late samples remain queryable but never replace runtime snapshots.';

create index telemetry_history_robot_ingested_idx
    on public.robot_telemetry_history (robot_id, ingested_at desc);
create index telemetry_history_ingested_idx
    on public.robot_telemetry_history (ingested_at desc);

select partman.create_parent(
    p_parent_table := 'public.robot_telemetry_history',
    p_control := 'source_timestamp',
    p_type := 'range',
    p_interval := '1 day',
    p_premake := 7,
    p_jobmon := false
);
update partman.part_config
set retention = '30 days',
    retention_keep_table = false,
    retention_keep_index = false,
    infinite_time_partitions = true
where parent_table = 'public.robot_telemetry_history';

create table public.bridge_health_history (
    id bigint generated always as identity primary key,
    bridge_id text not null,
    status text not null,
    robot_ids text[] not null,
    source_timestamp timestamptz not null,
    ingested_at timestamptz not null default now(),
    delivered_samples bigint not null,
    failed_deliveries bigint not null,
    last_error text,
    constraint bridge_health_id_not_blank check (char_length(btrim(bridge_id)) between 1 and 100),
    constraint bridge_health_status check (status in ('CONNECTED', 'DEGRADED')),
    constraint bridge_health_robot_ids_not_empty check (cardinality(robot_ids) > 0),
    constraint bridge_health_counters_nonnegative
        check (delivered_samples >= 0 and failed_deliveries >= 0),
    unique (bridge_id, source_timestamp)
);
create index bridge_health_latest_idx
    on public.bridge_health_history (bridge_id, source_timestamp desc);

create table public.task_state_history (
    id bigint generated always as identity primary key,
    task_id text not null,
    status text not null,
    assigned_robot_id text,
    attempt integer not null,
    message text not null default '',
    source_timestamp timestamptz not null,
    ingested_at timestamptz not null default now(),
    constraint task_history_id_not_blank check (char_length(btrim(task_id)) between 1 and 100),
    constraint task_history_attempt_nonnegative check (attempt >= 0),
    unique (task_id, source_timestamp)
);
create index task_history_task_timestamp_idx
    on public.task_state_history (task_id, source_timestamp desc);
create index task_history_retention_idx on public.task_state_history (source_timestamp);

create table public.alerts (
    id uuid primary key default gen_random_uuid(),
    dedupe_key text not null,
    severity public.alert_severity not null,
    code text not null,
    status public.alert_status not null default 'ACTIVE',
    message text not null,
    robot_id text,
    task_id text,
    operation_id uuid references public.commands (operation_id) on delete restrict,
    triggered_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    cleared_at timestamptz,
    constraint alerts_dedupe_key_not_blank check (char_length(btrim(dedupe_key)) between 1 and 200),
    constraint alerts_code_not_blank check (char_length(btrim(code)) between 1 and 100),
    constraint alerts_message_not_blank check (char_length(btrim(message)) between 1 and 1000),
    constraint alerts_status_timestamps check (
        (status = 'ACTIVE' and cleared_at is null)
        or (status = 'CLEARED' and cleared_at is not null and triggered_at <= cleared_at)
    )
);
create unique index alerts_one_active_dedupe_idx on public.alerts (dedupe_key)
    where status = 'ACTIVE';
create index alerts_status_triggered_idx on public.alerts (status, triggered_at desc);
create index alerts_retention_idx on public.alerts (triggered_at);

alter table public.robot_telemetry_history enable row level security;
alter table public.bridge_health_history enable row level security;
alter table public.task_state_history enable row level security;
alter table public.alerts enable row level security;

revoke all on table public.robot_telemetry_history, public.bridge_health_history,
    public.task_state_history, public.alerts from anon, authenticated;
grant select on table public.robot_telemetry_history, public.bridge_health_history,
    public.task_state_history, public.alerts to authenticated;
grant select, insert, update on table public.robot_telemetry_history,
    public.bridge_health_history, public.task_state_history, public.alerts to service_role;
grant usage, select on sequence public.bridge_health_history_id_seq,
    public.task_state_history_id_seq to service_role;

create policy telemetry_history_read on public.robot_telemetry_history for select to authenticated
using ((select private.is_active_user()));
create policy bridge_health_read on public.bridge_health_history for select to authenticated
using ((select private.is_active_user()));
create policy task_history_read on public.task_state_history for select to authenticated
using ((select private.is_active_user()));
create policy alerts_read on public.alerts for select to authenticated
using ((select private.is_active_user()));

select cron.schedule(
    'ev-twin-partman-maintenance',
    '15 * * * *',
    'call partman.run_maintenance_proc()'
);

create function private.prune_runtime_history()
returns void language plpgsql security definer set search_path = '' as $$
begin
    delete from public.alerts where triggered_at < now() - interval '90 days';
    delete from public.task_state_history where source_timestamp < now() - interval '90 days';
    delete from public.kpi_snapshots where recorded_at < now() - interval '90 days';
end;
$$;
revoke all on function private.prune_runtime_history() from public, anon, authenticated;
grant execute on function private.prune_runtime_history() to service_role;
select cron.schedule(
    'ev-twin-runtime-history-retention',
    '35 2 * * *',
    'select private.prune_runtime_history()'
);
