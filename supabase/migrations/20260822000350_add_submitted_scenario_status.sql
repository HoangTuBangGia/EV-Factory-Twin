-- PostgreSQL requires a commit before a newly added enum value can be used.

alter type public.scenario_status add value if not exists 'SUBMITTED' after 'SIMULATED';
