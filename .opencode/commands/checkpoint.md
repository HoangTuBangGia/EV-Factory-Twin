---
description: Verify current work and prepare it for human commit
agent: build
model: codelypixverse-openai/gpt-5.6-sol
---

Do not implement new functionality.

Read and obey `AGENTS.md`.

Inspect the current repository diff.

Verify:

1. implementation matches the requested checkpoint
2. relevant targeted tests pass
3. all applicable quality gates pass
4. relevant builds succeed
5. CI verifies the behavior where appropriate
6. documentation matches implementation
7. architecture and contracts remain valid
8. no generated/build artifacts were accidentally introduced
9. no unnecessary dependency was introduced
10. no speculative abstraction was introduced
11. no duplicate implementation was introduced
12. Git history was not modified by the agent

Then invoke the independent `reviewer`.

Resolve BLOCKING findings before declaring the checkpoint ready.

Finally output:

CHECKPOINT READY FOR HUMAN COMMIT

Summary:
...

Changed files:
...

Documentation:
...

Verification:
...

CI/build impact:
...

Known limitations:
...

Suggested commit message:
...

Next recommended checkpoint:
...

Waiting for you to review and git commit this checkpoint.

STOP.