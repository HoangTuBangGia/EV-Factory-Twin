---
description: Execute exactly one professional engineering checkpoint
agent: build
model: codelypixverse-openai/gpt-5.6-sol
---

Work on exactly one logical checkpoint:

$ARGUMENTS

Read and obey `AGENTS.md`.

Execute:

RESEARCH
→ REPOSITORY INSPECTION
→ ARCHITECTURE / CONTRACT CHECK
→ PLAN
→ IMPLEMENT
→ TARGETED TESTS
→ FULL QUALITY GATES
→ DOCUMENTATION
→ CI / BUILD VERIFICATION
→ INDEPENDENT REVIEW
→ CHECKPOINT SUMMARY
→ STOP FOR HUMAN COMMIT

Apply Ponytail principles:

YAGNI
→ reuse
→ native functionality
→ existing dependency
→ minimum sufficient implementation

Do not implement speculative future functionality.

Do not begin another logical checkpoint automatically.

Do not perform:

git add
git commit
git push
git merge
git rebase
git reset
git restore
git clean
git checkout
git switch
git stash

If a required system prerequisite is missing, report it instead of modifying
the host operating system.