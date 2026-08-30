"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { commitFactorySnapshot, fetchFactorySnapshot } from "@/lib/factory-snapshot";
import { fixtureAlerts, fixtureMetrics, fixtureRobots, fixtureTasks } from "@/lib/fixtures";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

export function useInitialFactoryData() {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const generationRef = useRef(0);
  const activeRequestRef = useRef<AbortController | null>(null);
  const setConnectionStatus = useFactoryStore((store) => store.setConnectionStatus);

  const load = useCallback(async () => {
    const generation = ++generationRef.current;
    activeRequestRef.current?.abort(new DOMException("Snapshot superseded", "AbortError"));
    const controller = new AbortController();
    activeRequestRef.current = controller;
    setState("loading");
    try {
      if (usesMockData) {
        if (generation !== generationRef.current) return;
        commitFactorySnapshot({
          robots: fixtureRobots,
          tasks: fixtureTasks,
          metrics: fixtureMetrics,
          alerts: fixtureAlerts,
        });
        setConnectionStatus("MOCK");
      } else {
        const snapshot = await fetchFactorySnapshot({ signal: controller.signal });
        if (generation !== generationRef.current) return;
        commitFactorySnapshot(snapshot);
      }
      if (generation !== generationRef.current) return;
      setState("ready");
    } catch {
      if (generation === generationRef.current) setState("error");
    } finally {
      if (activeRequestRef.current === controller) activeRequestRef.current = null;
    }
  }, [setConnectionStatus]);

  useEffect(() => {
    void load();
    return () => {
      generationRef.current += 1;
      activeRequestRef.current?.abort(new DOMException("Factory data provider unmounted", "AbortError"));
      activeRequestRef.current = null;
    };
  }, [load]);
  return { state, retry: load };
}
