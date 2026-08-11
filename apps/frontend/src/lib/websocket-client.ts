import { factoryEventSchema, type FactoryEvent } from "@/schemas/websocket-event";

type Status = "CONNECTING" | "LIVE" | "OFFLINE";

export class FactorySocket {
  private socket: WebSocket | null = null;
  private retry = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;

  constructor(
    private readonly url: string,
    private readonly onEvent: (event: FactoryEvent) => void,
    private readonly onStatus: (status: Status) => void,
  ) {}

  connect() {
    this.stopped = false;
    this.onStatus("CONNECTING");
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => { this.retry = 0; this.onStatus("LIVE"); };
    this.socket.onmessage = (message) => {
      try {
        const parsed = factoryEventSchema.safeParse(JSON.parse(String(message.data)));
        if (parsed.success) this.onEvent(parsed.data);
        else if (process.env.NODE_ENV === "development") console.warn("Ignored invalid factory event", parsed.error);
      } catch {
        if (process.env.NODE_ENV === "development") console.warn("Ignored non-JSON factory event");
      }
    };
    this.socket.onerror = () => this.socket?.close();
    this.socket.onclose = () => {
      this.onStatus("OFFLINE");
      if (this.stopped) return;
      const delay = Math.min(1000 * 2 ** this.retry++, 10_000);
      this.timer = setTimeout(() => this.connect(), delay);
    };
  }

  disconnect() {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.socket?.close();
  }
}
