-- Bind simulated scenarios to immutable layouts and persist all authoritative MVP KPIs.

alter table public.scenarios
    add column layout_id text not null,
    add column layout_version integer not null,
    add column route_id text not null,
    add column robot_speed_mps double precision not null,
    add column charger_count smallint not null,
    add column route_distance_m double precision not null,
    add column congestion_multiplier double precision not null,
    add column fleet_utilization_percent double precision not null,
    add column starvation_events integer not null,
    add column congestion_percent double precision not null,
    add column travel_distance double precision not null,
    add column average_delivery_delay double precision not null,
    add constraint scenarios_layout_version_fk
        foreign key (layout_id, layout_version)
        references public.layout_versions (layout_id, version) on delete restrict,
    add constraint scenarios_route_id_not_blank
        check (char_length(btrim(route_id)) between 1 and 80),
    add constraint scenarios_robot_speed_range check (robot_speed_mps > 0.0 and robot_speed_mps <= 10.0),
    add constraint scenarios_charger_count_range check (charger_count between 1 and 20),
    add constraint scenarios_route_distance_positive check (route_distance_m > 0.0),
    add constraint scenarios_congestion_multiplier_range
        check (congestion_multiplier between 1.0 and 10.0),
    add constraint scenarios_utilization_range
        check (fleet_utilization_percent between 0.0 and 100.0),
    add constraint scenarios_starvation_nonnegative check (starvation_events >= 0),
    add constraint scenarios_congestion_range check (congestion_percent between 0.0 and 100.0),
    add constraint scenarios_travel_distance_nonnegative check (travel_distance >= 0.0),
    add constraint scenarios_delivery_delay_nonnegative check (average_delivery_delay >= 0.0);

create index scenarios_layout_version_created_at_idx
    on public.scenarios (layout_id, layout_version, created_at desc);

comment on constraint scenarios_layout_version_fk on public.scenarios is
    'A simulation always references the exact immutable layout version it evaluated.';
