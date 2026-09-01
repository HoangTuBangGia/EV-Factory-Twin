-- Make retained task events replayable and persist operator alert acknowledgement.

begin;

alter table public.task_state_history
    add column payload_id text,
    add column pickup_station_id text,
    add column dropoff_station_id text,
    add column max_retries integer;

update public.task_state_history
set payload_id = 'UNKNOWN',
    pickup_station_id = 'UNKNOWN',
    dropoff_station_id = 'UNKNOWN',
    max_retries = 0;

alter table public.task_state_history
    alter column payload_id set not null,
    alter column pickup_station_id set not null,
    alter column dropoff_station_id set not null,
    alter column max_retries set not null,
    add constraint task_history_payload_id_not_blank
        check (char_length(btrim(payload_id)) between 1 and 100),
    add constraint task_history_pickup_id_not_blank
        check (char_length(btrim(pickup_station_id)) between 1 and 100),
    add constraint task_history_dropoff_id_not_blank
        check (char_length(btrim(dropoff_station_id)) between 1 and 100),
    add constraint task_history_max_retries_nonnegative check (max_retries >= 0);

create index task_history_ingested_at_idx
    on public.task_state_history (ingested_at, id);

alter table public.alerts
    add column acknowledged_at timestamptz,
    add column acknowledged_by uuid references public.profiles (id) on delete restrict,
    add constraint alerts_acknowledgement_complete check (
        (acknowledged_at is null and acknowledged_by is null)
        or
        (acknowledged_at is not null and acknowledged_by is not null
            and acknowledged_at >= triggered_at)
    );

create or replace function private.prune_runtime_history()
returns void language plpgsql security definer set search_path = '' as $$
begin
    delete from public.alerts where triggered_at < now() - interval '90 days';
    delete from public.task_state_history where ingested_at < now() - interval '90 days';
    delete from public.kpi_snapshots where recorded_at < now() - interval '90 days';
end;
$$;

commit;
