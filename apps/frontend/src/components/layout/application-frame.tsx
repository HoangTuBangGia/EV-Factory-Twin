"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { DataProvider } from "@/components/layout/data-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { NextActionStrip } from "@/components/workflow/next-action-strip";

function ProtectedAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, isLoading, error, logout, refreshUser } = useAuth();
  const isOverview = pathname === "/";

  if (isLoading) return <main className="center-state">Restoring secure session…</main>;
  if (!user) {
    return (
      <main className="center-state">
        <p>{error ?? "Redirecting to login…"}</p>
        {error && (
          <div className="button-row">
            <button className="button" type="button" onClick={() => void logout()}>Sign out</button>
            <button className="button primary" type="button" onClick={() => void refreshUser()}>Retry</button>
          </div>
        )}
      </main>
    );
  }

  return (
    <DataProvider>
      <div className={`app-shell${isOverview ? " cockpit-shell" : ""}`}>
        <Sidebar />
        <div className="workspace">
          {!isOverview && <Topbar />}
          <main className={`content${isOverview ? " cockpit-content" : ""}`}>
            <NextActionStrip floating={isOverview} />
            {children}
          </main>
        </div>
      </div>
    </DataProvider>
  );
}

export function ApplicationFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login" || pathname === "/scene-probe") return children;
  return <ProtectedAppShell>{children}</ProtectedAppShell>;
}
