"use client";

import { useEffect, useState } from "react";
import {
  type ConnectionStatus,
  useFactoryStore,
} from "@/stores/factory-store";

export const DATA_STALE_AFTER_MS = 30_000;

export function formatDataFreshness(lastUpdateAt: number | null, now = Date.now()) {
  if (lastUpdateAt === null) return "Waiting for data";
  const elapsedSeconds = Math.floor(Math.max(0, now - lastUpdateAt) / 1_000);
  if (elapsedSeconds < 60) return `Updated ${elapsedSeconds}s ago`;
  if (elapsedSeconds < 3_600) return `Updated ${Math.floor(elapsedSeconds / 60)}m ago`;
  return `Updated ${new Date(lastUpdateAt).toLocaleString()}`;
}

export function isDataStale(
  status: ConnectionStatus,
  lastUpdateAt: number | null,
  now = Date.now(),
) {
  return status === "LIVE"
    && lastUpdateAt !== null
    && now - lastUpdateAt > DATA_STALE_AFTER_MS;
}

export function DataFreshnessIndicator({ cockpit = false }: { cockpit?: boolean }) {
  const lastUpdateAt = useFactoryStore((state) => state.lastUpdateAt);
  const status = useFactoryStore((state) => state.connectionStatus);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(timer);
  }, []);

  const stale = isDataStale(status, lastUpdateAt, now);
  return <span className={`data-freshness${cockpit ? " cockpit" : ""}${stale ? " stale" : ""}`}>
    <span>{formatDataFreshness(lastUpdateAt, now)}</span>
    {stale && <strong role="status">Data may be stale</strong>}
  </span>;
}
