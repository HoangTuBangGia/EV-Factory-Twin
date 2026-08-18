"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
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
        <h1>EV Factory Digital Twin</h1>
      </div>
      <div className="top-actions">
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
