-- Downsampled operational KPI history. This table intentionally does not
-- contain robot pose/velocity telemetry.

create table public.kpi_snapshots (
    id bigint generated always as identity primary key,
    scenario_id text references public.scenarios (id) on delete set null,
    recorded_at timestamptz not null default now(),
    simulated_elapsed_seconds double precision not null,
    completed_tasks integer not null,
    throughput_per_hour double precision not null,
    average_cycle_time_seconds double precision not null,
    active_tasks integer not null,
    queued_tasks integer not null,
    starvation_events integer not null,
    fleet_utilization_percent double precision not null,
    constraint kpi_snapshots_elapsed_finite_nonnegative
        check (
            simulated_elapsed_seconds >= 0.0
            and simulated_elapsed_seconds < 'Infinity'::double precision
        ),
    constraint kpi_snapshots_completed_tasks_nonnegative check (completed_tasks >= 0),
    constraint kpi_snapshots_throughput_finite_nonnegative
        check (throughput_per_hour >= 0.0 and throughput_per_hour < 'Infinity'::double precision),
    constraint kpi_snapshots_cycle_time_finite_nonnegative
        check (
            average_cycle_time_seconds >= 0.0
            and average_cycle_time_seconds < 'Infinity'::double precision
        ),
    constraint kpi_snapshots_active_tasks_nonnegative check (active_tasks >= 0),
    constraint kpi_snapshots_queued_tasks_nonnegative check (queued_tasks >= 0),
    constraint kpi_snapshots_starvation_events_nonnegative check (starvation_events >= 0),
    constraint kpi_snapshots_utilization_range
        check (fleet_utilization_percent between 0.0 and 100.0)
);

comment on table public.kpi_snapshots is
    'FactoryMetrics sampled once per 10 seconds of wall time; never write raw 10 Hz telemetry here.';
comment on column public.kpi_snapshots.recorded_at is
    'UTC wall-clock sample time. MVP writer cadence is one row every 10 seconds.';
comment on column public.kpi_snapshots.scenario_id is
    'Applied scenario when known; null means the default or unassociated mock-factory run.';

create index kpi_snapshots_recorded_at_idx
    on public.kpi_snapshots (recorded_at desc);
create index kpi_snapshots_scenario_recorded_at_idx
    on public.kpi_snapshots (scenario_id, recorded_at desc)
    where scenario_id is not null;
