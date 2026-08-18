import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  FactorySnapshotTimeoutError,
  fetchFactorySnapshot,
} from "./factory-snapshot";

const mocks = vi.hoisted(() => ({
  getRobots: vi.fn(),
  getTasks: vi.fn(),
  getMetrics: vi.fn(),
  getAlerts: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: mocks,
}));

describe("fetchFactorySnapshot", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    const never = new Promise(() => undefined);
    mocks.getRobots.mockReturnValue(never);
    mocks.getTasks.mockReturnValue(never);
    mocks.getMetrics.mockReturnValue(never);
    mocks.getAlerts.mockReturnValue(never);
  });

  afterEach(() => vi.useRealTimers());

  it("aborts and rejects a hanging snapshot at its deadline", async () => {
    const operation = fetchFactorySnapshot({ timeoutMs: 50 });
    const rejection = expect(operation).rejects.toBeInstanceOf(FactorySnapshotTimeoutError);

    await vi.advanceTimersByTimeAsync(50);
    await rejection;

    for (const apiCall of [
      mocks.getRobots,
      mocks.getTasks,
      mocks.getMetrics,
      mocks.getAlerts,
    ]) {
      const signal = apiCall.mock.calls[0]?.[0] as AbortSignal;
      expect(signal.aborted).toBe(true);
    }
  });

  it("propagates lifecycle cancellation to every REST request", async () => {
    const controller = new AbortController();
    const operation = fetchFactorySnapshot({ signal: controller.signal, timeoutMs: 1_000 });
    const rejection = expect(operation).rejects.toMatchObject({ name: "AbortError" });

    controller.abort(new DOMException("Unmounted", "AbortError"));

    await rejection;
    expect(mocks.getRobots.mock.calls[0]?.[0]).toMatchObject({ aborted: true });
  });
});
