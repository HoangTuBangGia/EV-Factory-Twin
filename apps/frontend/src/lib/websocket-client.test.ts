import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  FactorySocket,
  SOCKET_CLOSE_BUFFER_OVERFLOW,
  SOCKET_CLOSE_PROFILE_CHANGED,
  SOCKET_CLOSE_SYNC_FAILED,
  SOCKET_AUTH_TIMEOUT_MS,
  SOCKET_CLOSE_AUTH_TIMEOUT,
  SOCKET_CLOSE_PROTOCOL_ERROR,
  SOCKET_CLOSE_UNAUTHORIZED,
  SOCKET_PENDING_EVENT_LIMIT,
} from "./websocket-client";

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly url: string;
  readyState = FakeWebSocket.CONNECTING;
  sent: string[] = [];
  closeCalls: Array<[number | undefined, string | undefined]> = [];
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close(code?: number, reason?: string) {
    this.closeCalls.push([code, reason]);
    this.readyState = FakeWebSocket.CLOSING;
  }

  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  message(payload: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(payload) }));
  }

  closed(code: number) {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code } as CloseEvent);
  }
}

const authOk = {
  type: "auth.ok",
  data: {
    user_id: "11111111-1111-4111-8111-111111111111",
    display_name: "Demo Designer",
    role: "DESIGNER",
    expires_at: 1_800_000_000,
  },
};

const telemetry = {
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
};

describe("FactorySocket authentication", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("sends the access token first and waits for auth.ok and synchronization before LIVE", async () => {
    const onEvent = vi.fn();
    const onStatus = vi.fn();
    const onAuthenticated = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      onEvent,
      onStatus,
      onAuthenticated,
    );

    socket.connect();
    const transport = FakeWebSocket.instances[0];
    transport.open();

    expect(JSON.parse(transport.sent[0])).toEqual({
      type: "auth",
      access_token: "test-access-token",
    });
    expect(onStatus).toHaveBeenLastCalledWith("CONNECTING");
    expect(onEvent).not.toHaveBeenCalled();

    transport.message(authOk);
    await Promise.resolve();
    expect(onStatus).toHaveBeenLastCalledWith("LIVE");
    expect(onAuthenticated).toHaveBeenCalledWith(authOk.data, false);

    transport.message(telemetry);
    expect(onEvent).toHaveBeenCalledWith(telemetry);
  });

  it("buffers authenticated events until snapshot synchronization finishes", async () => {
    let finishSynchronization!: () => void;
    const synchronization = new Promise<void>((resolve) => {
      finishSynchronization = resolve;
    });
    const onEvent = vi.fn();
    const onStatus = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      onEvent,
      onStatus,
      () => synchronization,
    );

    socket.connect();
    const transport = FakeWebSocket.instances[0];
    transport.open();
    transport.message(authOk);
    transport.message(telemetry);

    expect(onStatus).toHaveBeenLastCalledWith("CONNECTING");
    expect(onEvent).not.toHaveBeenCalled();

    finishSynchronization();
    await synchronization;
    await Promise.resolve();
    expect(onStatus).toHaveBeenLastCalledWith("LIVE");
    expect(onEvent).toHaveBeenCalledWith(telemetry);
  });

  it("treats a pre-auth payload as a protocol violation without refreshing", () => {
    const onEvent = vi.fn();
    const onAuthFailure = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      onEvent,
      vi.fn(),
      vi.fn(),
      onAuthFailure,
    );
    socket.connect();
    const transport = FakeWebSocket.instances[0];
    transport.open();
    transport.message(telemetry);

    expect(onEvent).not.toHaveBeenCalled();
    expect(transport.closeCalls.at(-1)?.[0]).toBe(SOCKET_CLOSE_PROTOCOL_ERROR);
    transport.closed(SOCKET_CLOSE_PROTOCOL_ERROR);
    vi.advanceTimersByTime(30_000);
    expect(onAuthFailure).not.toHaveBeenCalled();
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("marks an authenticated ordinary reconnect for snapshot recovery", () => {
    const onAuthenticated = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      vi.fn(),
      onAuthenticated,
    );
    socket.connect();
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].message(authOk);
    FakeWebSocket.instances[0].closed(1006);

    vi.advanceTimersByTime(1_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
    FakeWebSocket.instances[1].open();
    FakeWebSocket.instances[1].message(authOk);

    expect(onAuthenticated).toHaveBeenNthCalledWith(1, authOk.data, false);
    expect(onAuthenticated).toHaveBeenNthCalledWith(2, authOk.data, true);
  });

  it("does not retry a rejected token and reports the auth close code", () => {
    const onAuthFailure = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "rejected-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
      onAuthFailure,
    );
    socket.connect();
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].closed(SOCKET_CLOSE_UNAUTHORIZED);
    vi.advanceTimersByTime(30_000);

    expect(onAuthFailure).toHaveBeenCalledWith(SOCKET_CLOSE_UNAUTHORIZED);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("backs off after a local auth-ack timeout without requesting token refresh", () => {
    const onAuthFailure = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "still-valid-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
      onAuthFailure,
    );
    socket.connect();
    const transport = FakeWebSocket.instances[0];
    transport.open();

    vi.advanceTimersByTime(SOCKET_AUTH_TIMEOUT_MS);
    expect(transport.closeCalls.at(-1)?.[0]).toBe(SOCKET_CLOSE_AUTH_TIMEOUT);
    transport.closed(SOCKET_CLOSE_AUTH_TIMEOUT);
    expect(onAuthFailure).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("caps events buffered while snapshot synchronization is pending", async () => {
    let finishSynchronization!: () => void;
    const synchronization = new Promise<void>((resolve) => {
      finishSynchronization = resolve;
    });
    const onStatus = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      onStatus,
      () => synchronization,
    );
    socket.connect();
    const transport = FakeWebSocket.instances[0];
    transport.open();
    transport.message(authOk);

    for (let index = 0; index <= SOCKET_PENDING_EVENT_LIMIT; index += 1) {
      transport.message(telemetry);
    }

    expect(transport.closeCalls.at(-1)?.[0]).toBe(SOCKET_CLOSE_BUFFER_OVERFLOW);
    finishSynchronization();
    await synchronization;
    await Promise.resolve();
    expect(onStatus).not.toHaveBeenCalledWith("LIVE");
  });

  it("keeps exponential backoff across repeated snapshot synchronization failures", async () => {
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      vi.fn(),
      () => Promise.reject(new Error("snapshot unavailable")),
    );
    socket.connect();
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].message(authOk);
    await Promise.resolve();
    await Promise.resolve();
    expect(FakeWebSocket.instances[0].closeCalls.at(-1)?.[0]).toBe(SOCKET_CLOSE_SYNC_FAILED);
    FakeWebSocket.instances[0].closed(SOCKET_CLOSE_SYNC_FAILED);

    vi.advanceTimersByTime(1_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
    FakeWebSocket.instances[1].open();
    FakeWebSocket.instances[1].message(authOk);
    await Promise.resolve();
    await Promise.resolve();
    FakeWebSocket.instances[1].closed(SOCKET_CLOSE_SYNC_FAILED);

    vi.advanceTimersByTime(1_999);
    expect(FakeWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it("refreshes an active changed profile before reconnecting on 4409", async () => {
    const refreshProfile = vi.fn().mockResolvedValue(undefined);
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      vi.fn(),
      vi.fn(),
      refreshProfile,
    );
    socket.connect();
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].closed(SOCKET_CLOSE_PROFILE_CHANGED);

    expect(refreshProfile).toHaveBeenCalledWith(SOCKET_CLOSE_PROFILE_CHANGED);
    vi.advanceTimersByTime(1_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
    await Promise.resolve();
    vi.advanceTimersByTime(1_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("cancels a pending reconnect on disconnect", () => {
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      vi.fn(),
    );
    socket.connect();
    FakeWebSocket.instances[0].closed(1006);
    socket.disconnect();
    vi.advanceTimersByTime(30_000);

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("reconnects immediately without leaving the old socket or backoff timer active", () => {
    const onStatus = vi.fn();
    const socket = new FactorySocket(
      "ws://localhost/ws/factory",
      "test-access-token",
      vi.fn(),
      onStatus,
    );
    socket.connect();
    const firstTransport = FakeWebSocket.instances[0];
    firstTransport.open();
    firstTransport.closed(1006);

    socket.reconnect();

    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(onStatus).toHaveBeenLastCalledWith("CONNECTING");
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });
});
