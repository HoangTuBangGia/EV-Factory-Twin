"use client";

import { useFactoryStore } from "@/stores/factory-store";

export function KpiGrid() {
  const metrics = useFactoryStore((s) => s.metrics);
  const robotRecord = useFactoryStore((s) => s.robots);
  const robots = Object.values(robotRecord);
  const items = [
    ["Throughput", `${metrics?.throughput_per_hour.toFixed(1) ?? "—"} tasks/h`, "Current simulated output"],
    ["Fleet online", `${robots.filter((r) => r.status !== "OFFLINE").length}/${robots.length}`, "Connected AMRs"],
    ["Average cycle", `${metrics?.average_cycle_time_seconds.toFixed(1) ?? "—"} s`, "Backend-calculated metric"],
    ["Starvation", String(metrics?.starvation_events ?? "—"), "Events in current run"],
    ["Active tasks", String(metrics?.active_tasks ?? "—"), `${metrics?.queued_tasks ?? 0} queued`],
  ];
  return <section className="grid kpi-grid">{items.map(([label,value,note]) => <article className="panel kpi" key={label}><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong><span className="kpi-note">{note}</span></article>)}</section>;
}
