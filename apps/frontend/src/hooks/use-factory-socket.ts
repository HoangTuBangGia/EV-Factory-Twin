"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  commitFactorySnapshot,
  fetchFactorySnapshot,
  type FactorySnapshot,
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
import { toastInfo } from "@/stores/toast-store";

export const PAUSED_FACTORY_EVENT_LIMIT = 500;

export function useFactorySocket(
  enabled: boolean,
  accessToken: string | null,
  refreshSession: () => Promise<void>,
  refreshUser: () => Promise<void>,
  invalidateSession: () => void,
) {
  const refreshAttemptedForToken = useRef<string | null>(null);
  const lifecycleGeneration = useRef(0);
  const socketRef = useRef<FactorySocket | null>(null);
  const reconnect = useCallback(() => socketRef.current?.reconnect(), []);

  useEffect(() => {
    if (usesMockData || !enabled || !accessToken) return;
    const lifecycle = ++lifecycleGeneration.current;
    let snapshotGeneration = 0;
    let synchronizing = false;
    let bufferedEvents: FactoryEvent[] = [];
    let activeSynchronization: Promise<void> | null = null;
    let activeSnapshotController: AbortController | null = null;
    let recoveryRequested = false;
    let pausedEvents: FactoryEvent[] = [];
    let pausedSnapshot: FactorySnapshot | null = null;
    let pauseOverflowWarned = false;
    let pausedBufferIncomplete = false;
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
      current.markDataUpdated();
    }

    function bufferPausedEvent(event: FactoryEvent) {
      if (pausedEvents.length >= PAUSED_FACTORY_EVENT_LIMIT) {
        pausedEvents.shift();
        pausedBufferIncomplete = true;
        if (!pauseOverflowWarned) {
          pauseOverflowWarned = true;
          toastInfo("Live update buffer is full; the oldest paused updates are being discarded.");
        }
      }
      pausedEvents.push(event);
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
            const pending = bufferedEvents;
            bufferedEvents = [];
            let latestReset = -1;
            for (let index = 0; index < pending.length; index += 1) {
              if (pending[index].type === "factory.reset") latestReset = index;
            }
            if (latestReset >= 0) {
              useFactoryStore.getState().clearMetricsHistory();
              useFactoryStore.getState().bumpFactoryRevision();
              bufferedEvents = pending.slice(latestReset + 1);
              continue;
            }

            if (useFactoryStore.getState().paused) {
              pausedSnapshot = snapshot;
              synchronizing = false;
              for (const event of pending) bufferPausedEvent(event);
              useFactoryStore.getState().setConnectionStatus("LIVE");
              return;
            }

            commitFactorySnapshot(snapshot);

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
      if (useFactoryStore.getState().paused) {
        bufferPausedEvent(event);
        return;
      }
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

    const unsubscribePause = useFactoryStore.subscribe((state, previous) => {
      if (!previous.paused && state.paused) {
        pauseOverflowWarned = false;
        pausedBufferIncomplete = false;
        return;
      }
      if (!previous.paused || state.paused) return;
      pauseOverflowWarned = false;
      if (state.connectionStatus === "OFFLINE") {
        pausedSnapshot = null;
        pausedEvents = [];
        pausedBufferIncomplete = false;
        return;
      }
      if (pausedBufferIncomplete) {
        pausedSnapshot = null;
        pausedEvents = [];
        pausedBufferIncomplete = false;
        void synchronizeSnapshot().catch(() => {
          requestRecovery("Paused event overflow snapshot synchronization failed");
        });
        return;
      }
      const snapshot = pausedSnapshot;
      const pending = pausedEvents;
      pausedSnapshot = null;
      pausedEvents = [];
      if (snapshot) commitFactorySnapshot(snapshot);
      for (const event of pending) receiveEvent(event);
    });

    const socket = new FactorySocket(
      env.wsUrl,
      accessToken,
      receiveEvent,
      (status) => {
        store.setConnectionStatus(status);
        if (status === "OFFLINE") {
          cancelSynchronization("WebSocket disconnected during snapshot synchronization");
          pausedSnapshot = null;
          pausedEvents = [];
          pauseOverflowWarned = false;
          pausedBufferIncomplete = false;
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
    socketRef.current = socket;
    socket.connect();
    return () => {
      lifecycleGeneration.current += 1;
      cancelSynchronization("Socket lifecycle ended");
      unsubscribePause();
      socket.disconnect();
      if (socketRef.current === socket) socketRef.current = null;
    };
  }, [accessToken, enabled, invalidateSession, refreshSession, refreshUser]);

  return reconnect;
}
