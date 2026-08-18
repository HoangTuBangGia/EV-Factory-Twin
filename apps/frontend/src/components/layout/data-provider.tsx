"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useFactorySocket } from "@/hooks/use-factory-socket";
import { useInitialFactoryData } from "@/hooks/use-initial-factory-data";
import { useMockTelemetry } from "@/hooks/use-mock-telemetry";

export function DataProvider({ children }: { children: ReactNode }) {
  const { accessToken, refreshSession, refreshUser, invalidateSession } = useAuth();
  const { state, retry } = useInitialFactoryData();
  useFactorySocket(
    state === "ready" && accessToken !== null,
    accessToken,
    refreshSession,
    refreshUser,
    invalidateSession,
  );
  useMockTelemetry();
  if (state === "loading") return <main className="center-state">Loading factory snapshot…</main>;
  if (state === "error") return <main className="center-state"><p>Unable to load factory data.</p><button onClick={() => void retry()}>Retry</button></main>;
  return children;
}
