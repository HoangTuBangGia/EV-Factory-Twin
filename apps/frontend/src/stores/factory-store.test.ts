import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureMetrics, fixtureRobots } from "@/lib/fixtures";
import { factoryEventSchema } from "@/schemas/websocket-event";
import {
  METRICS_HISTORY_SAMPLE_INTERVAL_MS,
  METRICS_HISTORY_WINDOW_MS,
  useFactoryStore,
} from "./factory-store";

describe("factory store realtime updates", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-13T08:00:00Z"));
    useFactoryStore.getState().setRobots(fixtureRobots);
    useFactoryStore.getState().clearMetricsHistory();
  });

  afterEach(() => {
    vi.useRealTimers();
  });
  it("updates the matching robot position", () => {
    const robot = fixtureRobots[0];
    useFactoryStore.getState().updateRobotTelemetry({ timestamp: new Date().toISOString(), robot_id: robot.id, pose: { x: 5, y: 2, yaw: 0 }, velocity: robot.velocity, battery: robot.battery, status: robot.status, task_id: robot.task_id, payload_id: robot.payload_id });
    expect(useFactoryStore.getState().robots[robot.id].pose.x).toBe(5);
  });
  it("rejects invalid external events without changing the store", () => {
    const before = useFactoryStore.getState().robots["AMR-01"];
    const result = factoryEventSchema.safeParse({ type: "robot.telemetry", data: { robot_id: "AMR-01", battery: 999 } });
    expect(result.success).toBe(false);
    expect(useFactoryStore.getState().robots["AMR-01"]).toEqual(before);
  });
  it("accepts charging movement telemetry and factory reset events", () => {
    const telemetry = factoryEventSchema.safeParse({
      type: "robot.telemetry",
      data: {
        timestamp: new Date().toISOString(), robot_id: "AMR-01",
        pose: { x: 2, y: 12, yaw: 1.57 }, velocity: { linear: 1.2, angular: 0 },
        battery: 19, status: "MOVING_TO_CHARGER", task_id: null, payload_id: null,
      },
    });
    const reset = factoryEventSchema.safeParse({ type: "factory.reset", data: null });

    expect(telemetry.success).toBe(true);
    expect(reset.success).toBe(true);
  });

  it("updates current metrics immediately but samples chart history every five seconds", () => {
    useFactoryStore.getState().setMetrics({
      ...fixtureMetrics,
      throughput_per_hour: 1,
    });
    const initialHistory = useFactoryStore.getState().metricsHistory;

    vi.advanceTimersByTime(METRICS_HISTORY_SAMPLE_INTERVAL_MS - 1);
    useFactoryStore.getState().setMetrics({
      ...fixtureMetrics,
      throughput_per_hour: 2,
    });

    expect(useFactoryStore.getState().metrics?.throughput_per_hour).toBe(2);
    expect(useFactoryStore.getState().metricsHistory).toBe(initialHistory);
    expect(useFactoryStore.getState().metricsHistory).toHaveLength(1);

    vi.advanceTimersByTime(1);
    useFactoryStore.getState().setMetrics({
      ...fixtureMetrics,
      throughput_per_hour: 3,
    });

    expect(useFactoryStore.getState().metricsHistory).toHaveLength(2);
    expect(useFactoryStore.getState().metricsHistory.at(-1)?.throughput_per_hour).toBe(3);
  });

  it("retains at most 60 five-second samples", () => {
    for (let index = 0; index <= 60; index += 1) {
      useFactoryStore.getState().setMetrics({
        ...fixtureMetrics,
        throughput_per_hour: index,
      });
      vi.advanceTimersByTime(METRICS_HISTORY_SAMPLE_INTERVAL_MS);
    }

    const history = useFactoryStore.getState().metricsHistory;
    expect(history).toHaveLength(60);
    expect(history[0].throughput_per_hour).toBe(1);
    expect(history.at(-1)?.throughput_per_hour).toBe(60);
  });

  it("drops samples outside the five-minute window", () => {
    useFactoryStore.getState().setMetrics(fixtureMetrics);
    vi.advanceTimersByTime(METRICS_HISTORY_WINDOW_MS + 1);
    useFactoryStore.getState().setMetrics({
      ...fixtureMetrics,
      throughput_per_hour: 99,
    });

    const history = useFactoryStore.getState().metricsHistory;
    expect(history).toHaveLength(1);
    expect(history[0].throughput_per_hour).toBe(99);
  });

  it("clears metric history when the factory resets", () => {
    useFactoryStore.getState().setMetrics(fixtureMetrics);
    useFactoryStore.getState().clearMetricsHistory();

    expect(useFactoryStore.getState().metricsHistory).toEqual([]);
  });

  it("clears user-scoped factory data on logout", () => {
    useFactoryStore.getState().setMetrics(fixtureMetrics);
    useFactoryStore.getState().selectRobot(fixtureRobots[0].id);
    useFactoryStore.getState().reset();

    const state = useFactoryStore.getState();
    expect(state.robots).toEqual({});
    expect(state.tasks).toEqual({});
    expect(state.metrics).toBeNull();
    expect(state.metricsHistory).toEqual([]);
    expect(state.alerts).toEqual([]);
    expect(state.selectedRobotId).toBeNull();
    expect(state.connectionStatus).toBe("OFFLINE");
  });
});
