"use client";

import { useEffect, useRef } from "react";
import {
  commitFactorySnapshot,
  fetchFactorySnapshot,
} from "@/lib/factory-snapshot";
import { env, usesMockData } from "@/lib/env";
import {
  FactorySocket,
  SOCKET_CLOSE_PROFILE_CHANGED,
  SOCKET_CLOSE_FORBIDDEN,
  SOCKET_CLOSE_UNAUTHORIZED,
  SOCKET_PENDING_EVENT_LIMIT,
} from "@/lib/websocket-client";
import type { FactoryEvent } from "@/schemas/websocket-event";
import { useFactoryStore } from "@/stores/factory-store";

export function useFactorySocket(
  enabled: boolean,
  accessToken: string | null,
  refreshSession: () => Promise<void>,
  refreshUser: () => Promise<void>,
  invalidateSession: () => void,
) {
  const refreshAttemptedForToken = useRef<string | null>(null);
  const lifecycleGeneration = useRef(0);

  useEffect(() => {
    if (usesMockData || !enabled || !accessToken) return;
    const lifecycle = ++lifecycleGeneration.current;
    let snapshotGeneration = 0;
    let synchronizing = false;
    let bufferedEvents: FactoryEvent[] = [];
    let activeSynchronization: Promise<void> | null = null;
    let activeSnapshotController: AbortController | null = null;
    let recoveryRequested = false;
    const store = useFactoryStore.getState();

    function isCurrent(generation: number) {
      return lifecycleGeneration.current === lifecycle
        && snapshotGeneration === generation;
    }

    function applyEvent(event: FactoryEvent) {
      const current = useFactoryStore.getState();
      if (event.type === "robot.telemetry") current.updateRobotTelemetry(event.data);
      if (event.type === "task.updated") current.updateTask(event.data);
      if (event.type === "metrics.updated") current.setMetrics(event.data);
      if (event.type === "alert.created") current.addAlert(event.data);
      if (event.type === "alert.updated") current.addAlert(event.data);
      if (event.type === "command.updated") current.updateCommand(event.data);
    }

    function synchronizeSnapshot() {
      if (activeSynchronization) return activeSynchronization;
      synchronizing = true;
      useFactoryStore.getState().setConnectionStatus("CONNECTING");
      const generation = ++snapshotGeneration;

      activeSynchronization = (async () => {
        try {
          // A reset observed while the REST request is in flight invalidates
          // that snapshot. Fetch again, then replay only events after the most
          // recent reset so REST state can never overwrite newer telemetry.
          while (isCurrent(generation)) {
            const controller = new AbortController();
            activeSnapshotController = controller;
            let snapshot;
            try {
              snapshot = await fetchFactorySnapshot({ signal: controller.signal });
            } finally {
              if (activeSnapshotController === controller) activeSnapshotController = null;
            }
            if (!isCurrent(generation)) return;
            commitFactorySnapshot(snapshot);

            const pending = bufferedEvents;
            bufferedEvents = [];
            let latestReset = -1;
            for (let index = 0; index < pending.length; index += 1) {
              if (pending[index].type === "factory.reset") latestReset = index;
            }
            if (latestReset >= 0) {
              useFactoryStore.getState().clearMetricsHistory();
              bufferedEvents = pending.slice(latestReset + 1);
              continue;
            }

            synchronizing = false;
            for (const event of pending) applyEvent(event);
            useFactoryStore.getState().setConnectionStatus("LIVE");
            return;
          }
        } catch (error) {
          if (isCurrent(generation)) {
            bufferedEvents = [];
            useFactoryStore.getState().setConnectionStatus("OFFLINE");
          }
          throw error;
        } finally {
          if (isCurrent(generation)) {
            synchronizing = false;
            activeSynchronization = null;
          }
        }
      })();
      return activeSynchronization;
    }

    function cancelSynchronization(reason: string) {
      snapshotGeneration += 1;
      bufferedEvents = [];
      synchronizing = false;
      activeSynchronization = null;
      activeSnapshotController?.abort(new DOMException(reason, "AbortError"));
      activeSnapshotController = null;
    }

    function requestRecovery(reason: string) {
      if (recoveryRequested || lifecycleGeneration.current !== lifecycle) return;
      recoveryRequested = true;
      cancelSynchronization(reason);
      useFactoryStore.getState().setConnectionStatus("OFFLINE");
      socket.requestRecovery(reason);
    }

    function receiveEvent(event: FactoryEvent) {
      if (synchronizing) {
        if (bufferedEvents.length >= SOCKET_PENDING_EVENT_LIMIT) {
          requestRecovery("Factory event buffer overflow during snapshot recovery");
          return;
        }
        bufferedEvents.push(event);
        return;
      }
      if (event.type === "factory.reset") {
        useFactoryStore.getState().clearMetricsHistory();
        useFactoryStore.getState().bumpFactoryRevision();
        void synchronizeSnapshot().catch(() => {
          requestRecovery("Factory reset snapshot synchronization failed");
        });
        return;
      }
      applyEvent(event);
    }

    const socket = new FactorySocket(
      env.wsUrl,
      accessToken,
      receiveEvent,
      (status) => {
        store.setConnectionStatus(status);
        if (status === "OFFLINE") {
          cancelSynchronization("WebSocket disconnected during snapshot synchronization");
        }
      },
      async () => {
        recoveryRequested = false;
        // A token refresh creates a new FactorySocket instance, so an
        // instance-local "reconnected" flag cannot prove whether events were
        // missed. Refetching after every auth.ok is cheap and deterministic.
        useFactoryStore.getState().clearMetricsHistory();
        await synchronizeSnapshot();
      },
      async (closeCode) => {
        if (closeCode === SOCKET_CLOSE_FORBIDDEN) {
          invalidateSession();
          return;
        }
        if (closeCode === SOCKET_CLOSE_PROFILE_CHANGED) {
          await refreshUser();
          return;
        }
        if (
          closeCode === SOCKET_CLOSE_UNAUTHORIZED
          && refreshAttemptedForToken.current !== accessToken
        ) {
          refreshAttemptedForToken.current = accessToken;
          await refreshSession();
        }
      },
    );
    socket.connect();
    return () => {
      lifecycleGeneration.current += 1;
      cancelSynchronization("Socket lifecycle ended");
      socket.disconnect();
    };
  }, [accessToken, enabled, invalidateSession, refreshSession, refreshUser]);
}
