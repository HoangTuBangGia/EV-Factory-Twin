"use client";

import { useFactoryStore } from "@/stores/factory-store";

export function Topbar() {
  const status = useFactoryStore((s) => s.connectionStatus);
  return <header className="topbar"><div><div className="eyebrow">Battery intralogistics</div><h1>EV Factory Digital Twin</h1></div><div className="top-actions"><span className={`status ${status}`}><i className="status-dot"/>{status}</span><span className="muted">Designer</span></div></header>;
}
