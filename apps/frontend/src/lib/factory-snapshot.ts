import { apiClient } from "@/lib/api-client";
import type { FactoryAlert } from "@/schemas/alert";
import type { FactoryMetrics } from "@/schemas/metric";
import type { Robot } from "@/schemas/robot";
import type { Task } from "@/schemas/task";
import { useFactoryStore } from "@/stores/factory-store";

export interface FactorySnapshot {
  robots: Robot[];
  tasks: Task[];
  metrics: FactoryMetrics;
  alerts: FactoryAlert[];
}

export const FACTORY_SNAPSHOT_TIMEOUT_MS = 10_000;

export class FactorySnapshotTimeoutError extends Error {
  constructor() {
    super("Factory snapshot request timed out");
    this.name = "FactorySnapshotTimeoutError";
  }
}

interface FactorySnapshotOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

function abortReason(signal: AbortSignal) {
  return signal.reason instanceof Error
    ? signal.reason
    : new DOMException("Factory snapshot request aborted", "AbortError");
}

export async function fetchFactorySnapshot({
  signal,
  timeoutMs = FACTORY_SNAPSHOT_TIMEOUT_MS,
}: FactorySnapshotOptions = {}): Promise<FactorySnapshot> {
  const controller = new AbortController();
  const forwardAbort = () => controller.abort(signal?.reason);
  if (signal?.aborted) forwardAbort();
  else signal?.addEventListener("abort", forwardAbort, { once: true });

  const timeout = setTimeout(() => {
    controller.abort(new FactorySnapshotTimeoutError());
  }, timeoutMs);
  const aborted = new Promise<never>((_resolve, reject) => {
    if (controller.signal.aborted) {
      reject(abortReason(controller.signal));
      return;
    }
    controller.signal.addEventListener(
      "abort",
      () => reject(abortReason(controller.signal)),
      { once: true },
    );
  });

  try {
    const snapshot = Promise.all([
      apiClient.getRobots(controller.signal),
      apiClient.getTasks(controller.signal),
      apiClient.getMetrics(controller.signal),
      apiClient.getAlerts(controller.signal),
    ]).then(([robots, tasks, metrics, alerts]) => ({ robots, tasks, metrics, alerts }));
    return await Promise.race([snapshot, aborted]);
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", forwardAbort);
  }
}

export function commitFactorySnapshot(snapshot: FactorySnapshot) {
  const store = useFactoryStore.getState();
  store.setRobots(snapshot.robots);
  store.setTasks(snapshot.tasks);
  store.setMetrics(snapshot.metrics);
  store.setAlerts(snapshot.alerts);
}

export async function refetchFactorySnapshot(options?: FactorySnapshotOptions) {
  const snapshot = await fetchFactorySnapshot(options);
  commitFactorySnapshot(snapshot);
}
