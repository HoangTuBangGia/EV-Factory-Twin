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

## AI Engineering Architecture

OpenCode is the sole implementation orchestrator. The project uses one model: GPT-5.6 Sol. Different engineering responsibilities are represented by agents and prompts, not by different models.

```text
HUMAN
  ↓
OpenCode → GPT-5.6 Sol
  ↓
Researcher / Specialists / Reviewer
  ↓
Ponytail (YAGNI / minimal)
  ↓
shell/tools → RTK → uv / npm / make / colcon
  ↓
tests + docs + CI
  ↓
STOP → HUMAN GIT COMMIT
```

## Model Policy

The only approved model for project agents is `codelypixverse-openai/gpt-5.6-sol`.

Do not introduce another model or provider without explicit human approval.

Model specialization is achieved through agent role, system prompt, repository context, permissions, and tool access rather than multiple models.

## OpenCode

OpenCode owns research coordination, repository inspection, architecture checking, planning, delegation, implementation, testing, documentation coordination, CI/build verification, independent review, and checkpoint control.

No other AI tool owns project implementation orchestration.

## Ponytail

Ponytail is the project's YAGNI and implementation-minimization layer.

Preference order:

```text
do not build unnecessary functionality
↓
reuse existing project functionality
↓
use standard/native functionality
↓
reuse existing dependencies
↓
minimum sufficient new implementation
```

Ponytail must never justify weakening validation, security, error handling, type safety, tests, documentation, observability, accessibility, architecture boundaries, or CI gates.

Ponytail changes implementation style. It does not change Definition of Done.

Do not build speculative abstractions solely for possible future extensions.

## RTK

RTK is a transparent shell-output optimization layer. Agents issue normal commands such as:

```bash
git status
git diff
pytest
ruff check .
npm test
colcon test
```

RTK may transparently optimize supported command output through its OpenCode integration. Agents should not explicitly wrap normal commands with `rtk`.

RTK never changes acceptance criteria. If compressed output hides information needed to diagnose a failure, obtain enough detailed/raw diagnostic output before modifying code.

RTK is developer tooling only. It must not become a project dependency or CI dependency.

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

## Mandatory Development Workflow

Every non-trivial checkpoint:

```text
RESEARCH
↓
REPOSITORY INSPECTION
↓
ARCHITECTURE / CONTRACT CHECK
↓
PLAN
↓
IMPLEMENT
↓
TARGETED TESTS
↓
FULL QUALITY GATES
↓
DOCUMENTATION
↓
BUILD / CI VERIFICATION
↓
INDEPENDENT REVIEW
↓
CHECKPOINT SUMMARY
↓
STOP
↓
HUMAN GIT COMMIT
```

Do not automatically begin another logical checkpoint.

Final response must contain:

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

Then stop. Do not continue until the human explicitly asks to continue.
