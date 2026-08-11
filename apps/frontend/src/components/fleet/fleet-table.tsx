"use client";

import { useMemo, useState } from "react";
import { useFactoryStore } from "@/stores/factory-store";
import { Battery } from "./battery";
import { StatusBadge } from "./status-badge";

type Filter = "ALL" | "ACTIVE" | "IDLE" | "CHARGING" | "WARNING" | "ERROR";
const active = ["MOVING_TO_PICKUP", "PICKING", "DELIVERING", "DROPPING"];

export function FleetTable({ compact = false }: { compact?: boolean }) {
  const robotRecord = useFactoryStore((s) => s.robots);
  const robots = useMemo(() => Object.values(robotRecord), [robotRecord]);
  const selectRobot = useFactoryStore((s) => s.selectRobot);
  const [filter, setFilter] = useState<Filter>("ALL");
  const shown = useMemo(() => robots.filter((r) => filter === "ALL" || (filter === "ACTIVE" && active.includes(r.status)) || r.status === filter || (filter === "WARNING" && r.battery < 20)), [robots, filter]);
  return <>{!compact && <div className="toolbar panel-body">{(["ALL","ACTIVE","IDLE","CHARGING","WARNING","ERROR"] as Filter[]).map((f) => <button className={`filter ${filter === f ? "active" : ""}`} onClick={() => setFilter(f)} key={f}>{f}</button>)}</div>}<div className="table-wrap"><table className="data-table"><thead><tr><th>Robot</th><th>Status</th><th>Battery</th>{!compact && <><th>Speed</th><th>Current task</th><th>Payload</th><th>Last seen</th></>}</tr></thead><tbody>{shown.map((r) => <tr key={r.id} onClick={() => selectRobot(r.id)}><td><strong>{r.id}</strong><div className="muted">{r.name}</div></td><td><StatusBadge value={r.status}/></td><td><Battery value={r.battery}/></td>{!compact && <><td>{r.velocity.linear.toFixed(1)} m/s</td><td>{r.task_id ?? "—"}</td><td>{r.payload_id ?? "—"}</td><td>{new Date(r.last_seen_at).toLocaleTimeString()}</td></>}</tr>)}</tbody></table>{shown.length === 0 && <div className="empty">No robots match this filter.</div>}</div></>;
}
