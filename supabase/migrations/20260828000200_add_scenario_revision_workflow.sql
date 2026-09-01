-- Structured Monitor feedback and immutable child revisions.
alter table public.scenarios
    add column if not exists review_note text,
    add column if not exists revision_of text references public.scenarios (id) on delete restrict;

alter table public.scenarios
    add constraint scenarios_review_note_length
        check (review_note is null or char_length(btrim(review_note)) between 1 and 1000),
    add constraint scenarios_revision_not_self
        check (revision_of is null or revision_of <> id);

alter table public.scenarios drop constraint scenarios_workflow_actor_timestamps;
alter table public.scenarios add constraint scenarios_workflow_actor_timestamps check (
    (status in ('DRAFT', 'SIMULATED', 'SUBMITTED')
        and reviewed_by is null and reviewed_at is null and review_note is null
        and applied_by is null and applied_at is null)
    or (status = 'APPROVED'
        and reviewed_by is not null and reviewed_at is not null and review_note is null
        and applied_by is null and applied_at is null)
    or (status = 'REJECTED'
        and reviewed_by is not null and reviewed_at is not null
        and applied_by is null and applied_at is null)
    or (status = 'REVISION_REQUESTED'
        and reviewed_by is not null and reviewed_at is not null and review_note is not null
        and applied_by is null and applied_at is null)
    or (status = 'APPLIED'
        and reviewed_by is not null and reviewed_at is not null and review_note is null
        and applied_by is not null and applied_at is not null and reviewed_at <= applied_at)
);

alter table public.scenario_reviews
    add column if not exists note text,
    drop constraint scenario_reviews_decision_check,
    add constraint scenario_reviews_decision_check
        check (decision in ('SUBMITTED', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED')),
    add constraint scenario_reviews_note_length
        check (note is null or char_length(btrim(note)) between 1 and 1000),
    add constraint scenario_reviews_revision_note_required
        check ((decision = 'REVISION_REQUESTED' and note is not null)
            or (decision <> 'REVISION_REQUESTED' and note is null));

create or replace function private.record_scenario_review()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    if new.status is distinct from old.status
       and new.status in ('SUBMITTED', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED') then
        insert into public.scenario_reviews (scenario_id, decision, actor_id, note, created_at)
        values (
            new.id,
            new.status,
            case when new.status = 'SUBMITTED' then new.created_by else new.reviewed_by end,
            case when new.status = 'REVISION_REQUESTED' then new.review_note else null end,
            coalesce(new.reviewed_at, now())
        );
    end if;
    return new;
end;
$$;

create index scenarios_revision_of_created_at_idx
    on public.scenarios (revision_of, created_at desc)
    where revision_of is not null;

comment on column public.scenarios.review_note is
    'Current structured Monitor feedback; required for REVISION_REQUESTED.';
comment on column public.scenarios.revision_of is
    'Rejected/revision-requested scenario from which this immutable benchmark was derived.';
