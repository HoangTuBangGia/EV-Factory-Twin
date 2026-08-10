# ADR-0001: Use a Monorepo

## Status

Accepted

## Context

The project contains frontend, backend, simulation, evaluation and
ROS 2 components maintained by a four-person team.

## Decision

Use one Git repository containing all project components.

## Consequences

### Positive

- Atomic cross-component changes
- Single CI entry point
- Easier issue and release management
- Shared documentation

### Negative

- CI must use path filtering as the repository grows
- ROS and application dependencies require separate toolchains