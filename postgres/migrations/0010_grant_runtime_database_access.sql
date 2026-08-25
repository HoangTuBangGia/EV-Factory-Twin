begin;

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'ev_twin_app') then
        raise exception 'database role ev_twin_app must exist before migration 0010';
    end if;
end;
$$;

grant connect on database postgres to ev_twin_app;
grant usage on schema public to ev_twin_app;
grant select, insert, update, delete on all tables in schema public to ev_twin_app;
grant usage, select on all sequences in schema public to ev_twin_app;

alter default privileges for role postgres in schema public
grant select, insert, update, delete on tables to ev_twin_app;
alter default privileges for role postgres in schema public
grant usage, select on sequences to ev_twin_app;

commit;
