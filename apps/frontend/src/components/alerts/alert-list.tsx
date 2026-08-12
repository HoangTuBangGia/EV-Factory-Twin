"use client";

import { useFactoryStore } from "@/stores/factory-store";

export function AlertList({ limit }: { limit?: number }) {
  const alerts = useFactoryStore((s) => s.alerts); const shown = limit ? alerts.slice(0, limit) : alerts;
  return <div className="alert-list">{shown.map((a) => <article className={`alert ${a.severity}`} key={a.id}><div className="alert-top"><strong>{a.severity} · {a.code}</strong><time>{new Date(a.timestamp).toLocaleTimeString()}</time></div><p>{a.message}</p>{(a.robot_id || a.task_id) && <span className="muted">{[a.robot_id,a.task_id].filter(Boolean).join(" · ")}</span>}</article>)}{shown.length === 0 && <div className="empty">No active alerts.</div>}</div>;
}
