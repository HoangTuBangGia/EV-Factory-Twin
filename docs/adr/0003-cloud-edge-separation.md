# ADR-0003: Separate Factory Edge from Cloud Application Services

## Status

Accepted

## Context

The application needs cloud access and human approval while robot navigation must
not depend on public-network latency or availability.

## Decision

Use this production topology:

```text
Factory edge: Gazebo/robots -> ROS 2/Nav2 -> telemetry bridge
                                          -> outbound HTTPS/WSS
Cloud:        Render FastAPI -> Supabase PostgreSQL/Auth
Browser:      Vercel Next.js -> Render REST/WSS + Supabase Auth
```

- `/ws/factory` is the authenticated browser realtime endpoint.
- A separate machine-authenticated edge ingress will carry normalized telemetry
  and command acknowledgements. It must not reuse browser credentials.
- Browser commands go through FastAPI; the browser never accesses DDS or Nav2.
- Start the MVP/demo with one Free Render Web Service and one Uvicorn worker while
  live state and WebSocket membership are process-local. Use paid service for
  continuous operations where sleep and cold starts are unacceptable.
- Use Supabase PostgreSQL 17 without assuming TimescaleDB. Add native partitioning
  only when measured telemetry volume requires it.

## Consequences

- Render restarts interrupt sockets and current in-memory live state; clients and
  the edge bridge must reconnect and resynchronize.
- Horizontal backend scaling requires durable authoritative state and shared
  pub/sub before a second instance is enabled.
- The Render and Supabase regions should be colocated where practical.
