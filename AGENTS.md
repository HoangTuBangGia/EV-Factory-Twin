# EV Factory Digital Twin — Agent Engineering Guide

## Mission

Build a professional Digital Twin platform for AMR-based battery intralogistics in EV Final Assembly.

Current implementation scope is CORE only.

Core capabilities:

- realtime AMR telemetry
- ROS 2 / Gazebo integration
- AMR fleet and task lifecycle
- battery logistics
- realtime Digital Twin visualization
- KPI and congestion analysis
- SimPy what-if simulation and scenario comparison
- layout/configuration
- historical telemetry and replay
- human approval

Do not implement advanced extensions unless explicitly requested.

## Core Architecture

### Live Runtime

```text
Gazebo → ROS 2 → Telemetry Bridge → FastAPI → WebSocket → Next.js → Three.js
```

### Planning / What-if

```text
Scenario → SimPy → twin-core → KPI → FastAPI → Web UI
```

### Product Flow

```text
CREATE → SIMULATE → MEASURE → COMPARE → APPROVE → MONITOR
```

## Architecture Invariants

Never violate these without explicit human approval.

- Browser never communicates directly with ROS DDS.
- ROS/Gazebo realtime state flows through ROS → Telemetry Bridge → Backend → WebSocket → Frontend.
- MOCK, ROS, and REPLAY normalize into the same application telemetry contract.
- ROS packages are not members of the uv workspace.
- Shared business rules and authoritative KPI definitions belong in `twin-core`.
- Gazebo handles robotics, navigation, and physics validation; SimPy handles factory, logistics, and what-if simulation.
- Frontend does not define authoritative KPI formulas.
- REST is used for CRUD and queries. WebSocket is used for realtime state.
- No developer-specific absolute paths.
- Generated/build artifacts are not committed.
- A feature is incomplete without relevant tests, documentation, and build/CI verification.

## Canonical Technology Stack

### Python

- Python 3.12, uv, FastAPI, Pydantic
- SQLAlchemy, asyncpg, PostgreSQL, TimescaleDB
- SimPy, NumPy, Pandas

### Robotics

- Ubuntu 24.04 userspace
- ROS 2 Jazzy, Gazebo Harmonic, Nav2
- URDF/Xacro, rclpy, rosdep, colcon
- ament_cmake, ament_python

### Frontend

- Node.js 22, npm, Next.js, TypeScript
- Tailwind CSS, shadcn/ui, Zustand, Zod
- Three.js, React Three Fiber, ECharts

### Engineering

- Ruff, Mypy, Pytest
- Vitest, Testing Library, Playwright
- GitHub Actions, Docker, Docker Compose, GHCR, Nginx

Do not introduce competing technologies without explicit human approval.

## Repository Boundaries

| Path | Responsibility |
| --- | --- |
| `apps/backend` | FastAPI application |
| `apps/frontend` | Next.js application |
| `packages/twin-core` | Domain models, events, telemetry contracts, KPI definitions |
| `services/simulation` | SimPy simulation engine |
| `ros2_ws` | ROS 2, Gazebo, Nav2, telemetry bridge |
| `evaluation` | Benchmarks and evaluation |
| `tests/integration` | Cross-component integration tests |
| `docs` | Canonical project documentation |

## Package Manager Policy

### Python

Use uv only. Dependencies belong in `pyproject.toml` and `uv.lock`.

Never use `pip install` for project dependency management or introduce `requirements.txt` as a second dependency source of truth.

### Frontend

Use npm only. Commit `package-lock.json`; CI uses `npm ci`.

Do not introduce pnpm, yarn, or bun without explicit human approval.

### ROS

Dependencies belong in `package.xml`. Use `rosdep` and `colcon`. For ament_cmake packages, maintain `package.xml` and `CMakeLists.txt`.

## Host System

Agents must never directly mutate the host operating system using `sudo`, `apt`, `apt-get`, `pacman`, `yay`, `paru`, `dnf`, `yum`, or `brew`.

If a required system prerequisite is missing:

1. Identify it.
2. Document it.
3. Prefer the prepared WSL / Distrobox / container environment.
4. Stop and report the prerequisite.

## Build Policy

The root `Makefile` is the developer entry point where practical.

Relevant target families may include `sync`, `lint`, `format`, `format-check`, `typecheck`, `test`, `test-cov`, `check`, `frontend-check`, `ros-build`, `ros-test`, `integration`, and `docker-build`.

Do not create meaningless placeholder targets or root-level CMake configuration for components that do not require CMake.

## CI Policy

A feature is incomplete if CI cannot verify it.

Relevant workflows may include:

- `.github/workflows/ci.yml`
- `.github/workflows/ros-ci.yml`
- `.github/workflows/docker.yml`
- `.github/workflows/deploy.yml`

Rules:

- Local and CI workflows should share underlying commands where practical.
- Dependency lockfiles are authoritative.
- Do not weaken quality gates simply to obtain green CI.
- AI development tooling must never become a runtime or CI dependency.

## Testing Policy

Run targeted tests during implementation. Before checkpoint completion, run all applicable quality gates.

### Python

```bash
uv sync --locked --all-packages --dev
make check
```

### Frontend

When relevant, run `npm ci`, lint, typecheck, unit tests, and a production build.

### ROS

When relevant, verify dependencies and run `colcon build`, `colcon test`, and `colcon test-result`.

Cross-component behavior should receive integration tests where practical. Bug fixes should receive regression tests.

## Documentation Policy

Documentation is part of Definition of Done. Every logical checkpoint must create or update `docs/changes/<feature-slug>.md` using:

```markdown
# Change Title

## Summary

## Motivation

## Architecture / Contract Impact

## Files Changed

## Verification

## CI / Build Impact

## Follow-up
```

Update canonical documentation when affected: `README.md`, `docs/architecture.md`, `docs/development.md`, `docs/api.md`, `docs/evaluation.md`, `docs/deployment.md`, and `docs/adr/*`.

Documentation must describe actual implementation, not intended future behavior.


## Ponytail

Ponytail is the project's YAGNI and implementation-minimization layer. Work in
lazy senior developer mode: lazy means efficient, not careless. The best code
is the code never written.

Before writing code, understand the task and trace the real flow end to end.
Then stop at the first rung that holds:

```text
Does this need to be built at all? (YAGNI)
Does it already exist in this codebase? Reuse the existing helper, utility, or pattern.
Does the standard library already do this? Use it.
Does a native platform feature cover it? Use it.
Does an already-installed dependency solve it? Use it.
Can this be one line? Make it one line.
Only then: write the minimum code that works.
```

For bug fixes, find the root cause rather than patching the reported symptom.
Search every caller of a function you change and fix shared behavior once when
that is the correct boundary. Do not leave sibling callers broken.

Rules:

- No abstractions that were not explicitly requested.
- No new dependency when it can be avoided.
- No unrequested boilerplate.
- Prefer deletion over addition, boring over clever, and the fewest files possible.
- The shortest working diff wins only after the problem and correct change boundary are understood.
- Question complex requests when a simpler existing capability may cover the need.
- When equally small standard approaches exist, choose the edge-case-correct one.
- Mark a deliberate simplification with a real known ceiling (for example, a
  global lock, O(n²) scan, or naive heuristic) with a `ponytail` comment naming
  the ceiling and upgrade path.

Ponytail must never justify weakening input validation at trust boundaries,
security, error handling that prevents data loss, type safety, accessibility,
observability, architecture boundaries, CI gates, or calibration required by
real hardware.

Ponytail does not reduce Definition of Done. Anything explicitly requested
still applies. Non-trivial logic must leave behind the smallest runnable check
that would fail if the logic broke, preferably one focused existing-style test.
Avoid new test frameworks, fixtures, or infrastructure for that check. Trivial
one-line changes do not require a test.

Do not build speculative functionality or abstractions solely for possible
future extensions.

## RTK

RTK is an optional transparent shell-output optimization layer. Agents always
issue normal commands such as:

```bash
git status
git diff
pytest
ruff check .
npm test
colcon test
```

When RTK integration is available in the current environment, it may
transparently optimize supported command output. Agents must not explicitly
wrap commands with `rtk`. When RTK is unavailable, run the same commands
normally; do not install or configure RTK as a prerequisite.

RTK never changes acceptance criteria. If optimized output hides information
needed to diagnose a failure, obtain enough detailed/raw diagnostic output
before modifying code.

RTK is optional developer tooling only. It must not become a project, runtime,
build, or CI dependency.

## Source of Truth

Canonical project truth:

- source code
- tests
- documentation and ADRs
- domain/API contracts
- CI/build configuration

Non-authoritative:

- AI conversation history
- RTK statistics
- Ponytail runtime state

## Git Safety

Agents may inspect `git status`, `git diff`, `git log`, `git show`, `git branch`, `git rev-parse`, `git ls-files`, and `git grep`.

Agents must not perform `git add`, `git commit`, `git push`, `git merge`, `git rebase`, `git reset`, `git restore`, `git clean`, `git checkout`, `git switch`, or `git stash`.

The human owns Git history.

## Human-Controlled Execution

The human must understand and control project execution.

Before running any command that changes files, installs dependencies, starts
services, runs migrations, modifies containers, or affects external systems:

1. Explain what the command does.
2. Show the exact command.
3. State its expected effect and relevant risks.
4. Wait for explicit human approval.
5. Run only the approved command.

Agents may run read-only inspection commands without approval, including
`git status`, `git diff`, `rg`, `ls`, and reading files. Briefly state their
purpose before running them.

For tests, lint, type checks, and builds, show the exact command and wait for
approval unless the human explicitly authorized verification for the current
checkpoint.

Never combine an approved command with additional unapproved operations.

If the human requests command-only guidance, do not execute commands. Provide
the commands in execution order with a short explanation and wait for the
human to return the output.

## Token Efficiency

Minimize token use without weakening correctness.

- Keep plans, progress updates, and final summaries concise.
- Do not repeat information already available in the conversation.
- Use `rg`, targeted file reads, and concise Git output.
- Run targeted checks first. Run full quality gates only for non-trivial changes
  or when explicitly requested.
- Prefer quiet test output. Expand logs only when diagnosing a failure.
- Let RTK transparently optimize supported command output; never wrap commands
  with `rtk`.
- Apply Ponytail principles: reuse existing functionality and implement only the
  minimum sufficient change.
- Do not use subagents for trivial or tightly coupled work.
- Avoid reading generated files, lockfiles, build artifacts, and unrelated code
  unless required.
- For trivial checkpoints, respond only with the result, verification, and a
  suggested commit message.

## Development Workflow

For non-trivial code, architecture, or contract changes:

```text
INSPECT → CHECK ARCHITECTURE → PLAN → IMPLEMENT → TEST
→ DOCUMENT → VERIFY CI/BUILD → REVIEW → SUMMARIZE → HUMAN COMMIT
```

For trivial configuration, documentation, or formatting changes, perform only
proportionate inspection and validation. Do not run the full quality gates,
create change documentation, or request an independent review unless the change
has broader impact.

Do not automatically begin another logical checkpoint. Stop after completing
the requested checkpoint and wait for explicit human approval to continue.

For non-trivial checkpoints, the final response must contain:

```text
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
```

For trivial changes, provide only a concise summary, verification result, and
suggested commit message, then stop for human review and commit.
