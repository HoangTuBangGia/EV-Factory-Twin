-- Preserve explicit domain timestamps while retaining automatic update timestamps.

create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.updated_at is not distinct from old.updated_at then
        new.updated_at := now();
    end if;
    return new;
end;
$$;

comment on function private.set_updated_at() is
    'Uses database time only when the caller did not provide a new authoritative updated_at.';
