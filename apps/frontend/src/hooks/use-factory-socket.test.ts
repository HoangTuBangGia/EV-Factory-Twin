import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { FactoryEvent } from "@/schemas/websocket-event";
import { useFactoryStore } from "@/stores/factory-store";
import { useFactorySocket } from "./use-factory-socket";

const mocks = vi.hoisted(() => ({
  instances: [] as Array<{
    args: unknown[];
    connect: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    reconnect: ReturnType<typeof vi.fn>;
    requestRecovery: ReturnType<typeof vi.fn>;
  }>,
  fetchSnapshot: vi.fn(),
  commitSnapshot: vi.fn(),
}));

vi.mock("@/lib/env", () => ({
  env: { wsUrl: "ws://localhost/ws/factory" },
  usesMockData: false,
}));

vi.mock("@/lib/factory-snapshot", () => ({
  fetchFactorySnapshot: mocks.fetchSnapshot,
  commitFactorySnapshot: mocks.commitSnapshot,
}));

vi.mock("@/lib/websocket-client", () => ({
  SOCKET_CLOSE_UNAUTHORIZED: 4401,
  SOCKET_CLOSE_FORBIDDEN: 4403,
  SOCKET_CLOSE_PROFILE_CHANGED: 4409,
  SOCKET_PENDING_EVENT_LIMIT: 3,
  FactorySocket: class FactorySocket {
    connect = vi.fn();
    disconnect = vi.fn();
    reconnect = vi.fn();
    requestRecovery = vi.fn();

    constructor(...args: unknown[]) {
      mocks.instances.push({
        args,
        connect: this.connect,
        disconnect: this.disconnect,
        reconnect: this.reconnect,
        requestRecovery: this.requestRecovery,
      });
    }
  },
}));

describe("useFactorySocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.instances = [];
    mocks.fetchSnapshot.mockResolvedValue({ marker: "snapshot" });
    useFactoryStore.getState().reset();
  });

  it("reconnects with a refreshed token and refetches after each auth.ok", async () => {
    const refreshSession = vi.fn().mockResolvedValue(undefined);
    const invalidateSession = vi.fn();
    const { rerender } = renderHook(
      ({ token, enabled }) => useFactorySocket(
        enabled,
        token,
        refreshSession,
        vi.fn().mockResolvedValue(undefined),
        invalidateSession,
      ),
      { initialProps: { token: "old-token" as string | null, enabled: true } },
    );

    expect(mocks.instances).toHaveLength(1);
    expect(mocks.instances[0].connect).toHaveBeenCalledOnce();
    const firstAuthenticated = mocks.instances[0].args[4] as () => Promise<void>;
    await firstAuthenticated();
    expect(mocks.fetchSnapshot).toHaveBeenCalledTimes(1);
    expect(mocks.commitSnapshot).toHaveBeenCalledTimes(1);

    rerender({ token: "refreshed-token", enabled: true });
    expect(mocks.instances[0].disconnect).toHaveBeenCalledOnce();
    expect(mocks.instances).toHaveLength(2);
    const refreshedAuthenticated = mocks.instances[1].args[4] as () => Promise<void>;
    await refreshedAuthenticated();

    expect(mocks.fetchSnapshot).toHaveBeenCalledTimes(2);
    expect(mocks.commitSnapshot).toHaveBeenCalledTimes(2);
  });

  it("disconnects and cancels reconnect ownership when auth is removed", () => {
    const { rerender } = renderHook(
      ({ token, enabled }) => useFactorySocket(
        enabled,
        token,
        vi.fn().mockResolvedValue(undefined),
        vi.fn(),
        vi.fn(),
      ),
      { initialProps: { token: "active-token" as string | null, enabled: true } },
    );

    rerender({ token: null, enabled: false });
    expect(mocks.instances[0].disconnect).toHaveBeenCalledOnce();
    expect(mocks.instances).toHaveLength(1);
  });

  it("exposes manual reconnect for the active socket", () => {
    const { result, rerender } = renderHook(
      ({ token }) => useFactorySocket(true, token, vi.fn(), vi.fn(), vi.fn()),
      { initialProps: { token: "active-token" as string | null } },
    );

    result.current();
    expect(mocks.instances[0].reconnect).toHaveBeenCalledOnce();

    rerender({ token: null });
    result.current();
    expect(mocks.instances[0].reconnect).toHaveBeenCalledOnce();
  });

  it("does not commit an old snapshot after the access token changes", async () => {
    let resolveOld!: (snapshot: unknown) => void;
    let resolveNew!: (snapshot: unknown) => void;
    const oldSnapshot = new Promise((resolve) => { resolveOld = resolve; });
    const newSnapshot = new Promise((resolve) => { resolveNew = resolve; });
    mocks.fetchSnapshot
      .mockImplementationOnce(() => oldSnapshot)
      .mockImplementationOnce(() => newSnapshot);

    const { rerender } = renderHook(
      ({ token }) => useFactorySocket(true, token, vi.fn(), vi.fn(), vi.fn()),
      { initialProps: { token: "old-token" as string | null } },
    );
    const oldAuthentication = (mocks.instances[0].args[4] as () => Promise<void>)();

    rerender({ token: "new-token" });
    const oldOptions = mocks.fetchSnapshot.mock.calls[0]?.[0] as { signal: AbortSignal };
    expect(oldOptions.signal.aborted).toBe(true);
    const newAuthentication = (mocks.instances[1].args[4] as () => Promise<void>)();
    const currentSnapshot = { marker: "new" };
    resolveNew(currentSnapshot);
    await newAuthentication;
    expect(mocks.commitSnapshot).toHaveBeenCalledOnce();
    expect(mocks.commitSnapshot).toHaveBeenCalledWith(currentSnapshot);

    resolveOld({ marker: "stale" });
    await oldAuthentication;
    expect(mocks.commitSnapshot).toHaveBeenCalledOnce();
  });

  it("buffers events during reset recovery and replays them after the snapshot", async () => {
    const order: string[] = [];
    let resolveReset!: (snapshot: unknown) => void;
    const resetSnapshot = new Promise((resolve) => { resolveReset = resolve; });
    mocks.fetchSnapshot
      .mockResolvedValueOnce({ marker: "auth" })
      .mockImplementationOnce(() => resetSnapshot);
    mocks.commitSnapshot.mockImplementation((snapshot: { marker: string }) => {
      order.push(`snapshot:${snapshot.marker}`);
    });
    const originalUpdate = useFactoryStore.getState().updateRobotTelemetry;
    const telemetryUpdate = vi.fn(() => { order.push("telemetry"); });
    useFactoryStore.setState({ updateRobotTelemetry: telemetryUpdate });

    const { unmount } = renderHook(() => useFactorySocket(
      true,
      "active-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
    ));
    const onEvent = mocks.instances[0].args[2] as (event: FactoryEvent) => void;
    await (mocks.instances[0].args[4] as () => Promise<void>)();
    order.length = 0;

    onEvent({ type: "factory.reset", data: null });
    onEvent({
      type: "robot.telemetry",
      data: {
        timestamp: "2026-08-14T00:00:00.000Z",
        robot_id: "AMR-01",
        pose: { x: 1, y: 2, yaw: 0 },
        velocity: { linear: 1, angular: 0 },
        battery: 90,
        status: "DELIVERING",
        task_id: "TASK-0001",
        payload_id: "BP-0001",
      },
    });
    expect(telemetryUpdate).not.toHaveBeenCalled();

    resolveReset({ marker: "reset" });
    await resetSnapshot;
    await Promise.resolve();
    expect(order).toEqual(["snapshot:reset", "telemetry"]);

    unmount();
    useFactoryStore.setState({ updateRobotTelemetry: originalUpdate });
  });

  it("closes for recovery when a reset snapshot fails", async () => {
    mocks.fetchSnapshot
      .mockResolvedValueOnce({ marker: "auth" })
      .mockRejectedValueOnce(new Error("snapshot unavailable"));
    renderHook(() => useFactorySocket(
      true,
      "active-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
    ));
    await (mocks.instances[0].args[4] as () => Promise<void>)();
    const onEvent = mocks.instances[0].args[2] as (event: FactoryEvent) => void;

    onEvent({ type: "factory.reset", data: null });

    await vi.waitFor(() => expect(mocks.instances[0].requestRecovery).toHaveBeenCalledWith(
      "Factory reset snapshot synchronization failed",
    ));
    expect(useFactoryStore.getState().connectionStatus).toBe("OFFLINE");
  });

  it("aborts snapshot recovery and reconnects when its event buffer overflows", async () => {
    let holdReset!: () => void;
    const hangingReset = new Promise((resolve) => { holdReset = () => resolve({ marker: "late" }); });
    mocks.fetchSnapshot
      .mockResolvedValueOnce({ marker: "auth" })
      .mockImplementationOnce(() => hangingReset);
    const { unmount } = renderHook(() => useFactorySocket(
      true,
      "active-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
    ));
    await (mocks.instances[0].args[4] as () => Promise<void>)();
    const onEvent = mocks.instances[0].args[2] as (event: FactoryEvent) => void;
    onEvent({ type: "factory.reset", data: null });
    const resetOptions = mocks.fetchSnapshot.mock.calls[1]?.[0] as { signal: AbortSignal };

    for (let index = 0; index < 4; index += 1) {
      onEvent({ type: "factory.reset", data: null });
    }

    expect(resetOptions.signal.aborted).toBe(true);
    expect(mocks.instances[0].requestRecovery).toHaveBeenCalledOnce();
    expect(mocks.instances[0].requestRecovery).toHaveBeenCalledWith(
      "Factory event buffer overflow during snapshot recovery",
    );
    holdReset();
    await hangingReset;
    unmount();
  });

  it("refreshes the profile on 4409 without invalidating the session", async () => {
    const refreshUser = vi.fn().mockResolvedValue(undefined);
    const invalidateSession = vi.fn();
    renderHook(() => useFactorySocket(
      true,
      "active-token",
      vi.fn(),
      refreshUser,
      invalidateSession,
    ));
    const onAuthFailure = mocks.instances[0].args[5] as (code: number) => Promise<void>;

    await onAuthFailure(4409);

    expect(refreshUser).toHaveBeenCalledOnce();
    expect(invalidateSession).not.toHaveBeenCalled();
  });
});
