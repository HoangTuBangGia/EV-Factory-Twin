# Simulated Collision Alerts

## Summary

Canonical telemetry now activates and clears a durable CRITICAL collision alert
when conservative AMR footprint circles overlap.

## Motivation

The topic requires simulated collision measurement and abnormal-condition alerts.
Existing runtime health covered congestion but did not distinguish physical
footprint overlap.

## Architecture / Contract Impact

`twin-core` owns the footprint rule. Runtime Health evaluates only online robots
with accepted telemetry, deduplicates by sorted robot pair, persists through the
existing alert repository and broadcasts the existing alert WebSocket events.

## Files Changed

Twin-core collision rule, Backend/Frontend alert contracts, Runtime Health, tests
and API documentation.

## Verification

Pending the combined human-run quality gates after both final code checkpoints.

## CI / Build Impact

Covered by existing Python and Frontend checks; no migration or dependency added.

## Follow-up

Collision avoidance and automatic robot stopping remain outside the requested scope.
