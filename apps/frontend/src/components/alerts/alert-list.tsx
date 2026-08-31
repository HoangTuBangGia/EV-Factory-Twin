"use client";

import { useState } from "react";
import type { FactoryAlert } from "@/schemas/alert";
import { useFactoryStore } from "@/stores/factory-store";
import { toastInfo } from "@/stores/toast-store";

type SeverityFilter = "ALL" | FactoryAlert["severity"];
type AlertSort = "newest" | "severity";

const SEVERITY_RANK: Record<FactoryAlert["severity"], number> = {
  CRITICAL: 0,
  WARNING: 1,
  INFO: 2,
};

export function AlertList({ limit }: { limit?: number }) {
  const alerts = useFactoryStore((s) => s.alerts);
  const acknowledgedAlertIds = useFactoryStore((s) => s.acknowledgedAlertIds);
  const acknowledgeAlert = useFactoryStore((s) => s.acknowledgeAlert);
  const [severity, setSeverity] = useState<SeverityFilter>("ALL");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<AlertSort>("newest");
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const query = search.trim().toLocaleLowerCase();
  const acknowledged = new Set(acknowledgedAlertIds);
  const filtered = alerts
    .filter((alert) => alert.status === "ACTIVE")
    .filter((alert) => showAcknowledged || !acknowledged.has(alert.id))
    .filter((alert) => severity === "ALL" || alert.severity === severity)
    .filter((alert) => !query || [alert.robot_id, alert.task_id, alert.message]
      .some((value) => value?.toLocaleLowerCase().includes(query)))
    .sort((left, right) => sort === "severity"
      ? SEVERITY_RANK[left.severity] - SEVERITY_RANK[right.severity]
        || Date.parse(right.timestamp) - Date.parse(left.timestamp)
      : Date.parse(right.timestamp) - Date.parse(left.timestamp));
  const shown = limit ? filtered.slice(0, limit) : filtered;

  function acknowledge(alert: FactoryAlert) {
    acknowledgeAlert(alert.id);
    toastInfo("Acknowledged locally");
  }

  return <section className="alert-manager" aria-label="Alert management">
    <div className="alert-controls">
      <div className="toolbar alert-filters" role="group" aria-label="Filter alerts by severity">
        {(["ALL", "CRITICAL", "WARNING", "INFO"] as const).map((value) => <button
          className={`filter${severity === value ? " active" : ""}`}
          type="button"
          key={value}
          aria-pressed={severity === value}
          onClick={() => setSeverity(value)}
        >{value === "ALL" ? "All" : value[0] + value.slice(1).toLowerCase()}</button>)}
      </div>
      <label className="alert-search">
        <span className="sr-only">Search alerts</span>
        <input type="search" placeholder="Search robot, task, or message"
          value={search} onChange={(event) => setSearch(event.target.value)}/>
      </label>
      <div className="alert-options">
        <label>Sort
          <select aria-label="Sort alerts" value={sort}
            onChange={(event) => setSort(event.target.value as AlertSort)}>
            <option value="newest">Newest first</option>
            <option value="severity">Severity priority</option>
          </select>
        </label>
        <label className="alert-show-acknowledged">
          <input type="checkbox" checked={showAcknowledged}
            onChange={(event) => setShowAcknowledged(event.target.checked)}/>
          Show acknowledged
        </label>
      </div>
    </div>
    <div className="alert-list">{shown.map((alert) => {
      const isAcknowledged = acknowledged.has(alert.id);
      return <article className={`alert ${alert.severity}`} key={alert.id}>
        <div className="alert-top"><strong>{alert.severity} · {alert.code}</strong>
          <time dateTime={alert.timestamp}>{new Date(alert.timestamp).toLocaleTimeString()}</time></div>
        <p>{alert.message}</p>
        {(alert.robot_id || alert.task_id) && <span className="muted">
          {[alert.robot_id,alert.task_id].filter(Boolean).join(" · ")}
        </span>}
        {isAcknowledged
          ? <span className="alert-acknowledged">Acknowledged locally</span>
          : <button className="button compact" type="button"
              onClick={() => acknowledge(alert)}
              aria-label={`Acknowledge ${alert.severity} ${alert.code}`}>
              Acknowledge
            </button>}
      </article>;
    })}{shown.length === 0 && <div className="empty">No matching active alerts.</div>}</div>
  </section>;
}
