"use client";

import { useEffect } from "react";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

export function useMockTelemetry() {
  useEffect(() => {
    if (!usesMockData) return;
    let tick = 0;
    const timer = setInterval(() => {
      tick += 1;
      const store = useFactoryStore.getState();
      if (store.paused) return;
      for (const robot of Object.values(store.robots)) {
        if (!["DELIVERING", "MOVING_TO_PICKUP"].includes(robot.status)) continue;
        store.updateRobotTelemetry({
          timestamp: new Date().toISOString(), robot_id: robot.id,
          pose: { ...robot.pose, x: 2 + ((robot.pose.x - 2 + 0.12) % 15), y: robot.pose.y + Math.sin(tick / 8) * 0.025 },
          velocity: robot.velocity, battery: Math.max(0, robot.battery - 0.01), status: robot.status,
          task_id: robot.task_id, payload_id: robot.payload_id,
        });
      }
    }, 200);
    return () => clearInterval(timer);
  }, []);
}
