-- Preserve v1/v2 and append the connected route-network default as v3.

insert into public.layout_versions (layout_id, version, content, created_by)
select
    layouts.id,
    3,
    '{
      "width":120,
      "height":40,
      "stations":[
        {"id":"BATTERY_BUFFER","type":"BATTERY_BUFFER","x":32,"y":29},
        {"id":"MARRIAGE_STATION","type":"MARRIAGE_STATION","x":52,"y":6},
        {"id":"MARRIAGE_STATION_2","type":"MARRIAGE_STATION","x":82,"y":8},
        {"id":"CHARGING_STATION","type":"CHARGING_STATION","x":32,"y":11}
      ],
      "routes":[
        {
          "id":"BATTERY_DELIVERY","kind":"DELIVERY",
          "start_station_id":"BATTERY_BUFFER","end_station_id":"MARRIAGE_STATION",
          "waypoints":[{"x":32,"y":29},{"x":32,"y":20},{"x":40,"y":20},{"x":52,"y":20},{"x":52,"y":6}]
        },
        {
          "id":"BATTERY_DELIVERY_LONG","kind":"DELIVERY",
          "start_station_id":"BATTERY_BUFFER","end_station_id":"MARRIAGE_STATION_2",
          "waypoints":[{"x":32,"y":29},{"x":32,"y":20},{"x":40,"y":20},{"x":60,"y":20},{"x":82,"y":20},{"x":82,"y":8}]
        },
        {
          "id":"CHARGER_LINK","kind":"SUPPORT",
          "start_station_id":"CHARGING_STATION","end_station_id":"BATTERY_BUFFER",
          "waypoints":[{"x":32,"y":11},{"x":32,"y":20},{"x":32,"y":29}]
        }
      ],
      "no_go_zones":[{
        "id":"GIGA_PRESS_CLEARANCE",
        "points":[{"x":44,"y":27},{"x":58,"y":27},{"x":58,"y":37},{"x":44,"y":37}]
      }],
      "congestion_zones":[{
        "id":"WAREHOUSE_PRODUCTION_DOOR","delay_multiplier":1.25,
        "points":[{"x":38,"y":17.5},{"x":42,"y":17.5},{"x":42,"y":22.5},{"x":38,"y":22.5}]
      }],
      "config":{"robot_count":5,"demand_interval_seconds":8,"robot_speed_mps":1.2,"charger_count":2}
    }'::jsonb,
    layouts.created_by
from public.layouts as layouts
where layouts.id = 'LAYOUT-DEFAULT'
on conflict (layout_id, version) do nothing;

update public.layouts
set name = 'EV battery intralogistics plant',
    latest_version = greatest(latest_version, 3)
where id = 'LAYOUT-DEFAULT';
