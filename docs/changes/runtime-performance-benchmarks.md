# Runtime Performance Benchmarks

## Summary

Adds repeatable telemetry CSV analysis and a browser-render FPS benchmark.

## Motivation

The topic requires measurable telemetry latency/update frequency, collision
occurrences and render performance rather than qualitative claims.

## Architecture / Contract Impact

The evaluation package reads persisted accepted telemetry without changing the
runtime. The browser benchmark uses the existing Playwright dependency and the
fixture-backed production Three.js scene. Reports are generated under the ignored
`evaluation/reports` directory.

## Files Changed

Evaluation runtime module/tests, Frontend render benchmark script/package command,
README and evaluation documentation.

## Verification

Human-run `make check`, `make frontend-check`, ROS build and ROS tests passed.
A representative local ROS/Gazebo run produced 510 accepted samples from two
robots over 558.2 seconds. Runtime latency was 5.442 ms p50, 10.034 ms p95 and
3897.325 ms maximum, with a mean 0.455 Hz update rate and no observed collision
events. The headless Chromium/SwiftShader render baseline measured 7.55 average
FPS, 1033.2 ms p95 frame time and 21.15% of frames slower than 33.3 ms.

## CI / Build Impact

Unit/static checks cover the analyzers. Actual FPS and latency values are
environment-dependent acceptance evidence and are not CI pass/fail thresholds.

## Follow-up

Repeat the environment-dependent benchmarks on the final deployment hardware
during acceptance; the recorded headless software-rendered result is a local baseline.
