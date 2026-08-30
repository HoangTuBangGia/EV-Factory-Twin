"use client";

import { Suspense, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LivePauseButton } from "@/components/layout/live-pause-button";
import { useFactoryStore } from "@/stores/factory-store";

export function Topbar() {
  const status = useFactoryStore((s) => s.connectionStatus);
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    try {
      await logout();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <header className="topbar">
      <div>
        <div className="eyebrow">Battery intralogistics</div>
        <Suspense fallback={<div className="breadcrumb-fallback">EV Factory Digital Twin</div>}>
          <Breadcrumbs/>
        </Suspense>
      </div>
      <div className="top-actions">
        <LivePauseButton />
        <span className={`status ${status}`}><i className="status-dot" />{status}</span>
        {user && (
          <div className="user-summary">
            <strong>{user.display_name}</strong>
            <span>{user.role}</span>
          </div>
        )}
        <button className="button compact" type="button" disabled={signingOut} onClick={() => void signOut()}>
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>
    </header>
  );
}
