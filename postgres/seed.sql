-- Idempotent non-secret reference data for the GCP-native MVP database.

begin;

do $$
declare
    designer_id uuid;
begin
    select profiles.id
    into designer_id
    from public.profiles
    join public.app_users on app_users.id = profiles.id
    where profiles.role = 'DESIGNER'
      and profiles.is_active
    order by app_users.created_at
    limit 1;

    if designer_id is null then
        raise exception 'an active DESIGNER is required before applying postgres/seed.sql';
    end if;

    insert into public.layouts (id, name, latest_version, created_by)
    values ('LAYOUT-DEFAULT', 'Battery transfer zone', 1, designer_id)
    on conflict (id) do update
    set name = excluded.name,
        latest_version = greatest(public.layouts.latest_version, excluded.latest_version);

    insert into public.layout_versions (layout_id, version, content, created_by)
    values (
        'LAYOUT-DEFAULT',
        1,
        '{
          "width": 20,
          "height": 15,
          "stations": [
            {"id":"BATTERY_BUFFER","type":"BATTERY_BUFFER","x":2,"y":4},
            {"id":"MARRIAGE_STATION","type":"MARRIAGE_STATION","x":16,"y":8},
            {"id":"CHARGING_STATION","type":"CHARGING_STATION","x":2,"y":12}
          ],
          "routes": [{
            "id":"BATTERY_DELIVERY",
            "start_station_id":"BATTERY_BUFFER",
            "end_station_id":"MARRIAGE_STATION",
            "waypoints":[{"x":2,"y":4},{"x":8,"y":4},{"x":12,"y":8},{"x":16,"y":8}]
          }],
          "no_go_zones": [{
            "id":"NO_GO_01",
            "points":[{"x":8.4,"y":10.8},{"x":12.8,"y":10.8},{"x":12.8,"y":13.6},{"x":8.4,"y":13.6}]
          }],
          "congestion_zones": [{
            "id":"CONGESTION_01",
            "delay_multiplier":1.25,
            "points":[{"x":10,"y":6},{"x":13,"y":6},{"x":13,"y":9},{"x":10,"y":9}]
          }],
          "config":{"robot_count":2,"demand_interval_seconds":8,"robot_speed_mps":1,"charger_count":1}
        }'::jsonb,
        designer_id
    )
    on conflict (layout_id, version) do nothing;
end;
$$;

commit;
