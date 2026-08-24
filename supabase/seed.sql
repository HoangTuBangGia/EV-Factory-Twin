-- Factory Twin Seed Data
-- Safely inserts or updates the two MVP accounts in auth.users, auth.identities, and profiles.

create extension if not exists pgcrypto;

do $$
declare
  designer_id uuid;
  monitor_id uuid;
begin
  -----------------------------------------------------------------------------
  -- 1. Demo Designer (designer@example.com / Designer123!)
  -----------------------------------------------------------------------------
  select id into designer_id from auth.users where lower(email) = 'designer@example.com';
  if designer_id is null then
    designer_id := gen_random_uuid();
    insert into auth.users (
      instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
      raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
      confirmation_token, recovery_token, email_change_token_new, email_change,
      email_change_token_current, reauthentication_token, phone_change_token, phone_change
    ) values (
      '00000000-0000-0000-0000-000000000000', designer_id, 'authenticated', 'authenticated',
      'designer@example.com', crypt('Designer123!', gen_salt('bf')), now(),
      '{"provider":"email","providers":["email"],"app_role":"DESIGNER"}'::jsonb,
      '{"display_name":"Demo Designer"}'::jsonb, now(), now(),
      '', '', '', '',
      '', '', '', ''
    );
  else
    update auth.users
    set encrypted_password = crypt('Designer123!', gen_salt('bf')),
        raw_app_meta_data = '{"provider":"email","providers":["email"],"app_role":"DESIGNER"}'::jsonb,
        confirmation_token = '',
        recovery_token = '',
        email_change_token_new = '',
        email_change = '',
        email_change_token_current = '',
        reauthentication_token = '',
        phone_change_token = '',
        phone_change = '',
        updated_at = now()
    where id = designer_id;
  end if;

  insert into auth.identities (
    id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
  ) values (
    designer_id,
    'designer@example.com',
    designer_id,
    format('{"sub":"%s","email":"%s"}', designer_id, 'designer@example.com')::jsonb,
    'email',
    now(), now(), now()
  )
  on conflict (provider_id, provider) do update
  set identity_data = format('{"sub":"%s","email":"%s"}', designer_id, 'designer@example.com')::jsonb,
      updated_at = now();

  update public.profiles
  set display_name = 'Demo Designer', role = 'DESIGNER', is_active = true
  where id = designer_id;

  -----------------------------------------------------------------------------
  -- 2. Demo Monitor (monitor@example.com / Monitor123!)
  -----------------------------------------------------------------------------
  select id into monitor_id from auth.users where lower(email) = 'monitor@example.com';
  if monitor_id is null then
    monitor_id := gen_random_uuid();
    insert into auth.users (
      instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
      raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
      confirmation_token, recovery_token, email_change_token_new, email_change,
      email_change_token_current, reauthentication_token, phone_change_token, phone_change
    ) values (
      '00000000-0000-0000-0000-000000000000', monitor_id, 'authenticated', 'authenticated',
      'monitor@example.com', crypt('Monitor123!', gen_salt('bf')), now(),
      '{"provider":"email","providers":["email"],"app_role":"MONITOR"}'::jsonb,
      '{"display_name":"Demo Monitor"}'::jsonb, now(), now(),
      '', '', '', '',
      '', '', '', ''
    );
  else
    update auth.users
    set encrypted_password = crypt('Monitor123!', gen_salt('bf')),
        raw_app_meta_data = '{"provider":"email","providers":["email"],"app_role":"MONITOR"}'::jsonb,
        confirmation_token = '',
        recovery_token = '',
        email_change_token_new = '',
        email_change = '',
        email_change_token_current = '',
        reauthentication_token = '',
        phone_change_token = '',
        phone_change = '',
        updated_at = now()
    where id = monitor_id;
  end if;

  insert into auth.identities (
    id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
  ) values (
    monitor_id,
    'monitor@example.com',
    monitor_id,
    format('{"sub":"%s","email":"%s"}', monitor_id, 'monitor@example.com')::jsonb,
    'email',
    now(), now(), now()
  )
  on conflict (provider_id, provider) do update
  set identity_data = format('{"sub":"%s","email":"%s"}', monitor_id, 'monitor@example.com')::jsonb,
      updated_at = now();

  update public.profiles
  set display_name = 'Demo Monitor', role = 'MONITOR', is_active = true
  where id = monitor_id;

  -----------------------------------------------------------------------------
  -- 3. Default immutable layout version
  -----------------------------------------------------------------------------
  insert into public.layouts (id, name, latest_version, created_by)
  values ('LAYOUT-DEFAULT', 'EV battery intralogistics plant', 2, designer_id)
  on conflict (id) do update
  set name = excluded.name,
      latest_version = greatest(public.layouts.latest_version, excluded.latest_version);

  insert into public.layout_versions (layout_id, version, content, created_by)
  values (
    'LAYOUT-DEFAULT',
    2,
    '{
      "width": 120,
      "height": 40,
      "stations": [
        {"id":"BATTERY_BUFFER","type":"BATTERY_BUFFER","x":32,"y":29},
        {"id":"MARRIAGE_STATION","type":"MARRIAGE_STATION","x":52,"y":6},
        {"id":"CHARGING_STATION","type":"CHARGING_STATION","x":32,"y":11}
      ],
      "routes": [{
        "id":"BATTERY_DELIVERY",
        "start_station_id":"BATTERY_BUFFER",
        "end_station_id":"MARRIAGE_STATION",
        "waypoints":[{"x":32,"y":29},{"x":32,"y":20},{"x":40,"y":20},{"x":52,"y":20},{"x":52,"y":6}]
      }],
      "no_go_zones": [{
        "id":"GIGA_PRESS_CLEARANCE",
        "points":[{"x":44,"y":27},{"x":58,"y":27},{"x":58,"y":37},{"x":44,"y":37}]
      }],
      "congestion_zones": [{
        "id":"WAREHOUSE_PRODUCTION_DOOR",
        "delay_multiplier":1.25,
        "points":[{"x":38,"y":17.5},{"x":42,"y":17.5},{"x":42,"y":22.5},{"x":38,"y":22.5}]
      }],
      "config":{"robot_count":5,"demand_interval_seconds":8,"robot_speed_mps":1.2,"charger_count":2}
    }'::jsonb,
    designer_id
  )
  on conflict (layout_id, version) do nothing;

end $$;
