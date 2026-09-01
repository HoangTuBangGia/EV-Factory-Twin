"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { apiClient } from "@/lib/api-client";
import { usesMockData } from "@/lib/env";
import type { FactoryAlert } from "@/schemas/alert";
import { useFactoryStore } from "@/stores/factory-store";
import { toastError, toastInfo, toastSuccess } from "@/stores/toast-store";

type SeverityFilter = "ALL" | FactoryAlert["severity"];
type AlertSort = "newest" | "severity";

const SEVERITY_RANK: Record<FactoryAlert["severity"], number> = {
  CRITICAL: 0,
  WARNING: 1,
  INFO: 2,
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unable to acknowledge alert.";
}

export function AlertList({ limit, fixtureMode = usesMockData }: {
  limit?: number;
  fixtureMode?: boolean;
}) {
  const { user } = useAuth();
  const alerts = useFactoryStore((s) => s.alerts);
  const acknowledgedAlertIds = useFactoryStore((s) => s.acknowledgedAlertIds);
  const acknowledgeAlert = useFactoryStore((s) => s.acknowledgeAlert);
  const addAlert = useFactoryStore((s) => s.addAlert);
  const [severity, setSeverity] = useState<SeverityFilter>("ALL");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<AlertSort>("newest");
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);
  const query = search.trim().toLocaleLowerCase();
  const locallyAcknowledged = new Set(acknowledgedAlertIds);
  const isAcknowledged = (alert: FactoryAlert) => fixtureMode
    ? locallyAcknowledged.has(alert.id)
    : alert.acknowledged_at !== null;
  const filtered = alerts
    .filter((alert) => alert.status === "ACTIVE")
    .filter((alert) => showAcknowledged || !isAcknowledged(alert))
    .filter((alert) => severity === "ALL" || alert.severity === severity)
    .filter((alert) => !query || [alert.robot_id, alert.task_id, alert.message]
      .some((value) => value?.toLocaleLowerCase().includes(query)))
    .sort((left, right) => sort === "severity"
      ? SEVERITY_RANK[left.severity] - SEVERITY_RANK[right.severity]
        || Date.parse(right.timestamp) - Date.parse(left.timestamp)
      : Date.parse(right.timestamp) - Date.parse(left.timestamp));
  const shown = limit ? filtered.slice(0, limit) : filtered;

  async function acknowledge(alert: FactoryAlert) {
    if (fixtureMode) {
      acknowledgeAlert(alert.id);
      toastInfo("Acknowledged in fixture mode");
      return;
    }
    setAcknowledgingId(alert.id);
    try {
      addAlert(await apiClient.acknowledgeAlert(alert.id));
      toastSuccess("Alert acknowledged");
    } catch (error) {
      toastError(`Unable to acknowledge alert: ${errorMessage(error)}`);
    } finally {
      setAcknowledgingId(null);
    }
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
      const acknowledged = isAcknowledged(alert);
      return <article className={`alert ${alert.severity}`} key={alert.id}>
        <div className="alert-top"><strong>{alert.severity} · {alert.code}</strong>
          <time dateTime={alert.timestamp}>{new Date(alert.timestamp).toLocaleTimeString()}</time></div>
        <p>{alert.message}</p>
        {(alert.robot_id || alert.task_id) && <span className="muted">
          {[alert.robot_id,alert.task_id].filter(Boolean).join(" · ")}
        </span>}
        {acknowledged
          ? <span className="alert-acknowledged">
              {fixtureMode ? "Acknowledged in fixture mode" : "Acknowledged"}
            </span>
          : user?.role === "MONITOR" && <button className="button compact" type="button"
              disabled={acknowledgingId === alert.id}
              onClick={() => void acknowledge(alert)}
              aria-label={`Acknowledge ${alert.severity} ${alert.code}`}>
              {acknowledgingId === alert.id ? "Acknowledging…" : "Acknowledge"}
            </button>}
      </article>;
    })}{shown.length === 0 && <div className="empty">No matching active alerts.</div>}</div>
  </section>;
}
