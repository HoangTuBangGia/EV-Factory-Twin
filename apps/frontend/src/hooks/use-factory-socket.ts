"use client";

import { useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import { env, usesMockData } from "@/lib/env";
import { FactorySocket } from "@/lib/websocket-client";
import { useFactoryStore } from "@/stores/factory-store";

export function useFactorySocket(enabled: boolean) {
  useEffect(() => {
    if (usesMockData || !enabled) return;
    const store = useFactoryStore.getState();
    const socket = new FactorySocket(env.wsUrl, (event) => {
      const current = useFactoryStore.getState();
      if (event.type === "robot.telemetry") current.updateRobotTelemetry(event.data);
      if (event.type === "task.updated") current.updateTask(event.data);
      if (event.type === "metrics.updated") current.setMetrics(event.data);
      if (event.type === "alert.created") current.addAlert(event.data);
      if (event.type === "factory.reset") {
        void Promise.all([
          apiClient.getRobots(), apiClient.getTasks(), apiClient.getMetrics(), apiClient.getAlerts(),
        ]).then(([robots, tasks, metrics, alerts]) => {
          const latest = useFactoryStore.getState();
          latest.setRobots(robots);
          latest.setTasks(tasks);
          latest.setMetrics(metrics);
          latest.setAlerts(alerts);
        }).catch(() => current.setConnectionStatus("OFFLINE"));
      }
    }, store.setConnectionStatus);
    socket.connect();
    return () => socket.disconnect();
  }, [enabled]);
}
