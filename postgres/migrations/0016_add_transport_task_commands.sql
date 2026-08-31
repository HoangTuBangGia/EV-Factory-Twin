-- Extend the durable edge command channel with browser-created ROS transport tasks.

begin;

create type public.command_type as enum ('APPLY_SCENARIO', 'CREATE_TRANSPORT_TASK');

alter table public.commands
    add column command_type public.command_type not null default 'APPLY_SCENARIO',
    add column task_id text,
    alter column scenario_id drop not null;

alter table public.commands add constraint commands_target_matches_type check (
    (command_type = 'APPLY_SCENARIO' and scenario_id is not null and task_id is null)
    or
    (command_type = 'CREATE_TRANSPORT_TASK' and scenario_id is null and task_id is not null)
);
alter table public.commands add constraint commands_task_id_not_blank check (
    task_id is null or char_length(btrim(task_id)) between 1 and 100
);

create unique index commands_one_active_per_task_idx on public.commands (task_id)
    where command_type = 'CREATE_TRANSPORT_TASK'
      and status in ('PENDING', 'ACKNOWLEDGED');

commit;
