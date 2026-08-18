# AI-Assisted Development

## Purpose

AI tooling is used as a developer-acceleration layer.

It is not part of the EV Factory Digital Twin runtime.

The repository must remain buildable, testable, and maintainable without AI tooling.

---

## Final Tool Stack

The project uses:

| Component | Responsibility |
| --- | --- |
| OpenCode | implementation orchestration |
| GPT-5.6 Sol | all reasoning and implementation roles |
| Ponytail | YAGNI / minimum sufficient implementation |
| RTK | shell-output optimization |

No second model is used.

No separate AI project-management layer is used.

No AI knowledge-graph layer is used.

No model-context proxy is required.

---

## Authority

OpenCode is the sole implementation orchestrator.

GPT-5.6 Sol is used for:

- orchestration
- planning
- research
- architecture
- backend
- frontend
- ROS/Gazebo
- simulation
- QA/CI
- review
- documentation

Specialization comes from agent prompts and permissions rather than different models.

Ponytail affects implementation simplicity.

RTK affects shell-output transport.

Neither is a source of project truth.

The human owns Git history.

---

## Development Flow

```text
human request
      ↓
OpenCode /work
      ↓
GPT-5.6 Sol orchestrator
      ↓
research
      ↓
repository inspection
      ↓
architecture / contract check
      ↓
plan
      ↓
implementation
      │
      │ Ponytail minimizes unnecessary complexity
      ↓
targeted tests
      ↓
full quality gates
      │
      │ RTK reduces shell-output noise
      ↓
documentation
      ↓
CI/build verification
      ↓
independent review
      ↓
checkpoint summary
      ↓
STOP
      ↓
human Git commit
```

## OpenCode

Launch:

```bash
opencode
```

Execute exactly one logical checkpoint:

```text
/work <task>
```

Verify existing work without adding functionality:

```text
/checkpoint
```

OpenCode may inspect Git state.

OpenCode does not own Git history.

## Model

The only project model is:

```text
codelypixverse-openai/gpt-5.6-sol
```

Credentials:

```bash
export CODELYPIXVERSE_API_KEY="..."
```

Never commit API keys.

## Agent Roles

All agents use GPT-5.6 Sol:

- build
- plan
- researcher
- architect
- backend
- frontend
- ros-gazebo
- simulation
- qa-ci
- reviewer
- docs

The role definition controls behavior.

The model remains the same.

## Ponytail

Ponytail is configured through `opencode.json`.

Its implementation preference is:

```text
YAGNI
→ reuse
→ native functionality
→ existing dependencies
→ minimum sufficient new code
```

Ponytail must never weaken:

- validation
- security
- error handling
- type safety
- tests
- documentation
- observability
- accessibility
- architecture boundaries
- CI requirements

## RTK

RTK is installed globally in the developer environment.

OpenCode continues issuing normal shell commands.

RTK transparently optimizes supported command output.

RTK is not:

- a project runtime dependency
- a CI dependency
- a Python dependency
- a Node dependency
- a source of project truth

When compressed output is insufficient for debugging, obtain enough detailed/raw diagnostic output.

## Source of Truth

Canonical project truth:

- source code
- tests
- documentation
- ADRs
- domain/API contracts
- CI/build configuration

AI runtime state is advisory only.

## Git Policy

AI agents may inspect Git state.

The human performs:

- `git add`
- `git commit`
- `git push`
- merge
- rebase

Each OpenCode checkpoint stops before Git history changes.

## Package Manager Policy

Project dependencies:

| Area | Tooling |
| --- | --- |
| Python | uv |
| Frontend | npm |
| ROS | `package.xml` + rosdep + colcon |

Developer AI tooling:

| Tool | Installation |
| --- | --- |
| Ponytail | OpenCode plugin |
| RTK | Cargo-installed developer tool |

Neither is required by CI.
