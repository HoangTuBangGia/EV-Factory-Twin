-- PostgreSQL enum additions must commit before later migrations use the value.
alter type public.scenario_status
    add value if not exists 'REVISION_REQUESTED' after 'REJECTED';
