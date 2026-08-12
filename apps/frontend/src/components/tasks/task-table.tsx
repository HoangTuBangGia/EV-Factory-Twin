"use client";

import { useMemo } from "react";
import { useFactoryStore } from "@/stores/factory-store";
import { StatusBadge } from "@/components/fleet/status-badge";

function duration(start: string | null, end: string | null) { if (!start) return "—"; return end ? `${Math.max(0, Math.round((Date.parse(end)-Date.parse(start))/1000))} s` : "Running"; }
export function TaskTable({ compact = false }: { compact?: boolean }) {
  const taskRecord = useFactoryStore((s) => s.tasks);
  const tasks = useMemo(() => Object.values(taskRecord), [taskRecord]);
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>Task</th><th>Payload</th>{!compact && <><th>Pickup</th><th>Dropoff</th></>}<th>Robot</th><th>Status</th>{!compact && <><th>Created</th><th>Duration</th></>}</tr></thead><tbody>{tasks.map((t) => <tr key={t.task_id}><td><strong>{t.task_id}</strong></td><td>{t.payload_id}</td>{!compact && <><td>{t.pickup}</td><td>{t.dropoff}</td></>}<td>{t.assigned_robot_id ?? "—"}</td><td><StatusBadge value={t.status}/></td>{!compact && <><td>{new Date(t.created_at).toLocaleString()}</td><td>{duration(t.started_at,t.completed_at)}</td></>}</tr>)}</tbody></table>{tasks.length === 0 && <div className="empty">No active tasks.<br/>New battery delivery tasks will appear here.</div>}</div>;
}
