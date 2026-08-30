"use client";

import { useFactoryStore } from "@/stores/factory-store";

export function ConnectionBanner({ onReconnect }: { onReconnect: () => void }) {
  const status = useFactoryStore((state) => state.connectionStatus);

  if (status !== "OFFLINE" && status !== "CONNECTING") return null;
  const connecting = status === "CONNECTING";

  return (
    <div
      className={`connection-banner ${status}`}
      role={connecting ? "status" : "alert"}
      aria-live={connecting ? "polite" : "assertive"}
    >
      {connecting && <span className="connection-spinner" aria-hidden="true"/>}
      <p>
        <strong>{connecting ? "Reconnecting…" : "Live data disconnected."}</strong>
        {!connecting && " Displayed data may be stale."}
      </p>
      <button className="button compact" type="button" disabled={connecting} onClick={onReconnect}>
        Reconnect
      </button>
    </div>
  );
}
