"use client";

import { useFactoryStore } from "@/stores/factory-store";
import { Tooltip } from "@/components/ui/tooltip";

const KPI_HELP = {
  throughput: "Số task hoàn thành/giờ. Cao hơn = tốt hơn.",
  fleet: "Số AMR đang hoạt động / tổng fleet.",
  cycle: "Thời gian trung bình từ nhận task đến hoàn thành. Thấp hơn = tốt hơn.",
  starvation: "Số lần station yêu cầu battery nhưng không có AMR khả dụng. 0 = lý tưởng; >5 = cần thêm fleet.",
  active: "Số task đang được xử lý. Dòng ghi chú cho biết số task vẫn đang chờ.",
} as const;

export function KpiGrid() {
  const metrics = useFactoryStore((s) => s.metrics);
  const robotRecord = useFactoryStore((s) => s.robots);
  const robots = Object.values(robotRecord);
  const items = [
    ["throughput", "Throughput", `${metrics?.throughput_per_hour.toFixed(1) ?? "—"} tasks/h`, "Current simulated output"],
    ["fleet", "Fleet online", `${robots.filter((r) => r.status !== "OFFLINE").length}/${robots.length}`, "Connected AMRs"],
    ["cycle", "Average cycle", `${metrics?.average_cycle_time_seconds.toFixed(1) ?? "—"} s`, "Backend-calculated metric"],
    ["starvation", "Starvation", String(metrics?.starvation_events ?? "—"), "Events in current run"],
    ["active", "Active tasks", String(metrics?.active_tasks ?? "—"), `${metrics?.queued_tasks ?? 0} queued`],
  ] as const;
  return <section className="grid kpi-grid">{items.map(([key,label,value,note]) => {
    const tooltipId = `kpi-${key}-help`;
    const labelId = `kpi-${key}-label`;
    return <article className="panel kpi" key={key}
      aria-labelledby={labelId} aria-describedby={tooltipId}>
      <div className="kpi-heading">
        <span className="kpi-label" id={labelId}>{label}</span>
        <Tooltip contentId={tooltipId} label={`Explain ${label}`} content={KPI_HELP[key]}/>
      </div>
      <strong className="kpi-value">{value}</strong>
      <span className="kpi-note">{note}</span>
    </article>;
  })}</section>;
}
