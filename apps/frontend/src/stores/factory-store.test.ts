import { beforeEach, describe, expect, it } from "vitest";
import { fixtureRobots } from "@/lib/fixtures";
import { factoryEventSchema } from "@/schemas/websocket-event";
import { useFactoryStore } from "./factory-store";

describe("factory store realtime updates", () => {
  beforeEach(() => useFactoryStore.getState().setRobots(fixtureRobots));
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
});
