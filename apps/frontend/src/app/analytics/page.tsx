"use client";

import { useEffect, useState } from "react";
import {
  OperationsChart,
  OPERATIONS_TREND_LIVE_LABEL,
} from "@/components/charts/operations-chart";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { apiClient } from "@/lib/api-client";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

export default function AnalyticsPage() {
  const hydrateMetricsHistory = useFactoryStore((state) => state.hydrateMetricsHistory);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);

  useEffect(() => {
    if (usesMockData) return;
    let active = true;
    apiClient.getMetricHistory()
      .then((page) => {
        if (!active) return;
        hydrateMetricsHistory(page.items.map((item) => ({
          ...item.metrics,
          timestamp: Date.parse(item.recorded_at),
        })));
      })
      .catch(() => {
        // History is additive; current snapshot and WebSocket metrics stay usable.
        if (active) setHistoryUnavailable(true);
      });
    return () => { active = false; };
  }, [hydrateMetricsHistory]);

  return <>
    <header className="page-head"><div><h2>Analytics</h2><p>
      {usesMockData
        ? "Development KPI fixtures for local UI work."
        : "Persisted KPI history merged with live WebSocket updates."}
    </p></div></header>
    {historyUnavailable && <div className="notice" role="status">
      Historical KPI data is unavailable; live metrics will continue updating.
    </div>}
    <KpiGrid/>
    <div className="grid main-grid">
      <section className="panel"><div className="panel-head"><h3>Throughput trend</h3>
        <span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span>
      </div><OperationsChart mode="throughput"/></section>
      <section className="panel"><div className="panel-head"><h3>Cycle-time trend</h3>
        <span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span>
      </div><OperationsChart mode="cycle"/></section>
    </div>
  </>;
}
