# Workflow Usability Acceptance

## Purpose

Validate that the P0–P2 workflow can be completed without coaching by at least three representative
Designers and three representative Monitors. This is a human acceptance run, not an automated test.

## Safety and privacy

- Use staging accounts and staging factory data only.
- Identify participants as `D1`–`D3` and `M1`–`M3`; do not record names, email addresses,
  passwords, tokens, screenshots containing secrets, or production data.
- Do not guide a participant after the task starts. Record where they stop or ask for help.
- Do not apply a candidate to a real factory or production edge runtime.

## Preconditions

- Migrations `20260828000100` and `20260828000200` are present on the staging database.
- Staging Backend and Frontend run the same reviewed commit.
- Three active Designer accounts and three active Monitor accounts are available.
- The hosted Playwright revision workflow passes against the same staging environment.
- Each session starts with a unique candidate name so results do not collide.

## Tasks

### Designer

1. Find where to create or select a layout candidate.
2. Change a route or zone and save a candidate revision.
3. Simulate that layout, interpret the baseline comparison and submit it for review.
4. After a Monitor requests changes, find the feedback, create a revised candidate, run it and
   submit it again.
5. Explain whether the live factory changed and what must happen next.

### Monitor

1. Find a candidate awaiting review.
2. Compare its physical layout and KPI result with the current factory.
3. Request one specific change and verify that the candidate leaves the review queue.
4. Find the revised candidate, approve it and apply it.
5. Identify the command phase and explain when the live runtime actually changes.

## Session record

Copy one row per participant. Time begins after the task text is shown and stops when the participant
states that the task is complete.

| Participant | Role | Completed without help | Time | Help requests | First stopping point | Correct next-step explanation | Notes |
|---|---|---:|---:|---:|---|---:|---|
| D1 | Designer |  |  |  |  |  |  |
| D2 | Designer |  |  |  |  |  |  |
| D3 | Designer |  |  |  |  |  |  |
| M1 | Monitor |  |  |  |  |  |  |
| M2 | Monitor |  |  |  |  |  |  |
| M3 | Monitor |  |  |  |  |  |  |

## Acceptance decision

P3 passes only when:

- all six participants complete the critical role workflow without operator intervention;
- all six correctly explain the next step and when the live factory changes;
- no participant can perform an action forbidden to their role;
- the hosted revision Playwright suite passes; and
- every stopping point and help request is recorded, with follow-up issues linked before sign-off.

If any condition fails, record P3 as failed or pending. Fix the smallest shared cause, rerun the
relevant automated checks, then repeat the affected human sessions. Do not rewrite unsuccessful
observations as passes.

## Sign-off

| Field | Value |
|---|---|
| Commit tested |  |
| Staging frontend URL |  |
| Staging backend URL |  |
| Hosted E2E run |  |
| Facilitator |  |
| Date |  |
| Decision (`PASS` / `FAIL` / `PENDING`) | `PENDING` |
