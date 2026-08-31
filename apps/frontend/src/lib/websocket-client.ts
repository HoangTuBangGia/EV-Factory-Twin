import {
  factoryEventSchema,
  factorySocketAuthOkSchema,
  factorySocketAuthRequestSchema,
  type FactoryEvent,
  type FactorySocketAuthOk,
} from "@/schemas/websocket-event";

type Status = "CONNECTING" | "LIVE" | "OFFLINE";
type AuthenticatedUser = FactorySocketAuthOk["data"];

export const SOCKET_AUTH_TIMEOUT_MS = 5_000;
export const SOCKET_CLOSE_UNAUTHORIZED = 4_401;
export const SOCKET_CLOSE_FORBIDDEN = 4_403;
export const SOCKET_CLOSE_PROFILE_CHANGED = 4_409;
// Private client-side codes must not be confused with authoritative server
// auth rejections. In particular, a slow auth acknowledgement must reconnect
// with backoff instead of entering a token-refresh loop.
export const SOCKET_CLOSE_AUTH_TIMEOUT = 4_001;
export const SOCKET_CLOSE_SYNC_FAILED = 4_002;
export const SOCKET_CLOSE_PROTOCOL_ERROR = 4_003;
export const SOCKET_CLOSE_BUFFER_OVERFLOW = 4_004;
export const SOCKET_CLOSE_POLICY_VIOLATION = 1_008;
export const SOCKET_PENDING_EVENT_LIMIT = 1_000;

export class FactorySocket {
  private socket: WebSocket | null = null;
  private retry = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private authTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private authenticated = false;
  private synchronized = false;
  private authenticatedOnce = false;
  private pendingEvents: FactoryEvent[] = [];

  constructor(
    private readonly url: string,
    private readonly accessToken: string,
    private readonly onEvent: (event: FactoryEvent) => void,
    private readonly onStatus: (status: Status) => void,
    private readonly onAuthenticated: (
      user: AuthenticatedUser,
      reconnected: boolean,
    ) => void | Promise<void> = () => undefined,
    private readonly onAuthFailure: (closeCode: number) => void | Promise<void> = () => undefined,
  ) {}

  connect() {
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) return;
    this.stopped = false;
    this.authenticated = false;
    this.synchronized = false;
    this.pendingEvents = [];
    this.onStatus("CONNECTING");

    const socket = new WebSocket(this.url);
    this.socket = socket;
    socket.onopen = () => {
      if (this.socket !== socket || this.stopped) return;
      const request = factorySocketAuthRequestSchema.parse({
        type: "auth",
        access_token: this.accessToken,
      });
      socket.send(JSON.stringify(request));
      this.clearAuthTimer();
      this.authTimer = setTimeout(() => {
        if (this.socket === socket && !this.authenticated) {
          socket.close(SOCKET_CLOSE_AUTH_TIMEOUT, "Authentication timeout");
        }
      }, SOCKET_AUTH_TIMEOUT_MS);
    };
    socket.onmessage = (message) => {
      if (this.socket !== socket || this.stopped) return;
      let payload: unknown;
      try {
        payload = JSON.parse(String(message.data));
      } catch {
        socket.close(SOCKET_CLOSE_PROTOCOL_ERROR, "Invalid server response");
        return;
      }

      if (!this.authenticated) {
        const auth = factorySocketAuthOkSchema.safeParse(payload);
        if (!auth.success) {
          socket.close(SOCKET_CLOSE_PROTOCOL_ERROR, "Invalid authentication response");
          return;
        }
        const reconnected = this.authenticatedOnce;
        this.authenticated = true;
        this.authenticatedOnce = true;
        this.clearAuthTimer();
        void this.finishAuthentication(socket, auth.data.data, reconnected);
        return;
      }

      const parsed = factoryEventSchema.safeParse(payload);
      if (parsed.success) {
        if (this.synchronized) this.onEvent(parsed.data);
        else if (this.pendingEvents.length >= SOCKET_PENDING_EVENT_LIMIT) {
          this.pendingEvents = [];
          socket.close(SOCKET_CLOSE_BUFFER_OVERFLOW, "Factory event buffer overflow");
        } else this.pendingEvents.push(parsed.data);
      }
      else if (process.env.NODE_ENV === "development") {
        console.warn("Ignored invalid factory event", parsed.error);
      }
    };
    socket.onerror = () => socket.close();
    socket.onclose = (event) => {
      if (this.socket !== socket) return;
      this.socket = null;
      this.authenticated = false;
      this.synchronized = false;
      this.pendingEvents = [];
      this.clearAuthTimer();
      this.onStatus("OFFLINE");
      if (this.stopped) return;

      if (event.code === SOCKET_CLOSE_UNAUTHORIZED || event.code === SOCKET_CLOSE_FORBIDDEN) {
        void Promise.resolve(this.onAuthFailure(event.code)).catch(() => undefined);
        return;
      }
      if (event.code === SOCKET_CLOSE_PROFILE_CHANGED) {
        void this.refreshProfileAndReconnect(event.code);
        return;
      }
      if (
        event.code === SOCKET_CLOSE_POLICY_VIOLATION
        || event.code === SOCKET_CLOSE_PROTOCOL_ERROR
      ) return;

      this.scheduleReconnect();
    };
  }

  disconnect() {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.clearAuthTimer();
    const socket = this.socket;
    this.socket = null;
    this.authenticated = false;
    this.synchronized = false;
    this.pendingEvents = [];
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close(1_000, "Client disconnect");
    }
  }

  reconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.clearAuthTimer();
    const socket = this.socket;
    this.socket = null;
    this.authenticated = false;
    this.synchronized = false;
    this.pendingEvents = [];
    this.retry = 0;
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close(1_000, "Manual reconnect");
    }
    this.connect();
  }

  requestRecovery(reason = "Factory snapshot resynchronization required") {
    const socket = this.socket;
    this.pendingEvents = [];
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close(SOCKET_CLOSE_SYNC_FAILED, reason);
    }
  }

  private clearAuthTimer() {
    if (this.authTimer) clearTimeout(this.authTimer);
    this.authTimer = null;
  }

  private async finishAuthentication(
    socket: WebSocket,
    user: AuthenticatedUser,
    reconnected: boolean,
  ) {
    try {
      await this.onAuthenticated(user, reconnected);
      if (
        this.socket !== socket
        || this.stopped
        || !this.authenticated
        || socket.readyState !== WebSocket.OPEN
      ) return;
      this.retry = 0;
      this.synchronized = true;
      this.onStatus("LIVE");
      const pending = this.pendingEvents;
      this.pendingEvents = [];
      for (const event of pending) this.onEvent(event);
    } catch {
      if (this.socket === socket && !this.stopped) {
        socket.close(SOCKET_CLOSE_SYNC_FAILED, "Snapshot synchronization failed");
      }
    }
  }

  private scheduleReconnect() {
    if (this.stopped || this.reconnectTimer) return;
    const delay = Math.min(1_000 * 2 ** this.retry++, 10_000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private async refreshProfileAndReconnect(closeCode: number) {
    try {
      await this.onAuthFailure(closeCode);
    } catch {
      // The authenticated profile refresh owns its user-facing error state.
      // Reconnecting remains safe and lets a transient REST failure recover.
    } finally {
      this.scheduleReconnect();
    }
  }
}
