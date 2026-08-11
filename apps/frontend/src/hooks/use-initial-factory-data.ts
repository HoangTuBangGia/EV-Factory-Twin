"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { fixtureAlerts, fixtureMetrics, fixtureRobots, fixtureTasks } from "@/lib/fixtures";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

export function useInitialFactoryData() {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const { setRobots, setTasks, setMetrics, setAlerts, setConnectionStatus } = useFactoryStore();

  const load = useCallback(async () => {
    setState("loading");
    try {
      if (usesMockData) {
        setRobots(fixtureRobots); setTasks(fixtureTasks); setMetrics(fixtureMetrics); setAlerts(fixtureAlerts);
        setConnectionStatus("MOCK");
      } else {
        const [robots, tasks, metrics, alerts] = await Promise.all([
          apiClient.getRobots(), apiClient.getTasks(), apiClient.getMetrics(), apiClient.getAlerts(),
        ]);
        setRobots(robots); setTasks(tasks); setMetrics(metrics); setAlerts(alerts);
      }
      setState("ready");
    } catch { setState("error"); }
  }, [setAlerts, setConnectionStatus, setMetrics, setRobots, setTasks]);

  useEffect(() => { void load(); }, [load]);
  return { state, retry: load };
}
