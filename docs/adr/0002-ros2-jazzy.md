# ADR-0002: ROS 2 Jazzy, Gazebo Harmonic, and Nav2 at the Edge

## Status

Accepted

## Context

The CORE platform needs repeatable AMR navigation and physics validation without
exposing ROS DDS to browsers or the public internet. Ubuntu 24.04, ROS 2 Jazzy,
Gazebo Harmonic, and the Nav2 Jazzy release are the supported upstream pairing.

## Decision

- Run ROS 2, Gazebo, Nav2, fleet/task execution, and the telemetry bridge on an
  Ubuntu 24.04 factory-edge host or prepared development container.
- Use standard ROS messages and Nav2 actions before defining custom interfaces.
- Keep ROS packages in `ros2_ws`; they are not uv workspace members.
- Normalize ROS observations into the `twin-core` telemetry contract before they
  enter FastAPI.
- The edge initiates outbound authenticated TLS communication to the backend.
- Use SimPy for factory what-if evaluation and Gazebo for robotics/physics.

## Consequences

- DDS and robot control remain available during a cloud or WAN outage.
- Multi-robot namespaces, TF frames, simulation time, QoS, reconnect, and stale
  telemetry handling must be tested explicitly.
- Vercel, Render, and Supabase do not host the ROS runtime.
