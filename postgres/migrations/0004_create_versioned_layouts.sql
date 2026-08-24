-- Versioned factory layouts. Geometry/configuration rows are append-only.

create sequence public.layout_number_seq as bigint start with 1 increment by 1 cache 1;

create function private.next_layout_id()
returns text
language plpgsql
volatile
set search_path = ''
as $$
declare
    layout_number bigint;
    layout_number_text text;
begin
    layout_number := nextval('public.layout_number_seq');
    layout_number_text := layout_number::text;
    return 'LAYOUT-' || lpad(
        layout_number_text,
        greatest(4, char_length(layout_number_text)),
        '0'
    );
end;
$$;

revoke all on function private.next_layout_id()
    from public;

create table public.layouts (
    id text primary key default private.next_layout_id(),
    name text not null,
    latest_version integer not null default 1,
    created_by uuid not null references public.profiles (id) on delete restrict,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz,
    constraint layouts_id_format check (id ~ '^LAYOUT-[A-Z0-9_-]{1,64}$'),
    constraint layouts_name_not_blank check (char_length(btrim(name)) between 1 and 120),
    constraint layouts_latest_version_positive check (latest_version >= 1),
    constraint layouts_archive_time_order check (archived_at is null or archived_at >= created_at)
);

create table public.layout_versions (
    layout_id text not null references public.layouts (id) on delete restrict,
    version integer not null,
    content jsonb not null,
    created_by uuid not null references public.profiles (id) on delete restrict,
    created_at timestamptz not null default now(),
    primary key (layout_id, version),
    constraint layout_versions_version_positive check (version >= 1),
    constraint layout_versions_content_object check (jsonb_typeof(content) = 'object'),
    constraint layout_versions_required_content check (
        content ?& array[
            'width',
            'height',
            'stations',
            'routes',
            'no_go_zones',
            'congestion_zones',
            'config'
        ]
    )
);

comment on table public.layouts is
    'Mutable layout identity/metadata. DELETE in the API sets archived_at.';
comment on table public.layout_versions is
    'Immutable validated geometry and runtime configuration snapshots.';

create index layouts_active_created_at_idx
    on public.layouts (created_at, id)
    where archived_at is null;
create index layouts_created_by_created_at_idx
    on public.layouts (created_by, created_at desc);
create index layout_versions_created_at_idx
    on public.layout_versions (layout_id, created_at desc);

create trigger layouts_set_updated_at
before update on public.layouts
for each row
execute function private.set_updated_at();

create function private.reject_layout_version_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception 'layout_versions is append-only'
        using errcode = '42501';
end;
$$;

revoke all on function private.reject_layout_version_mutation()
    from public;

create trigger layout_versions_reject_update_delete
before update or delete on public.layout_versions
for each row
execute function private.reject_layout_version_mutation();

create trigger layout_versions_reject_truncate
before truncate on public.layout_versions
for each statement
execute function private.reject_layout_version_mutation();
