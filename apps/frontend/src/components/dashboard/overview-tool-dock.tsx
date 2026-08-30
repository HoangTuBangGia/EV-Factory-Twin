"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { AlertList } from "@/components/alerts/alert-list";
import { OperationsChart, OPERATIONS_TREND_LIVE_LABEL } from "@/components/charts/operations-chart";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { FleetTable } from "@/components/fleet/fleet-table";
import { LivePauseButton } from "@/components/layout/live-pause-button";
import { DataFreshnessIndicator } from "@/components/layout/data-freshness-indicator";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

type Tool = "metrics" | "fleet" | "alerts";

function MetricsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V10M10 19V5M16 19v-7M22 19H2"/></svg>;
}

function RobotIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5V2M8 2h8M5 9h14v9H5zM8 13h.01M16 13h.01M8 18v3M16 18v3M2 12h3M19 12h3"/></svg>;
}

function AlertIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2.5 20h19zM12 9v5M12 17h.01"/></svg>;
}

function ToolButton({ tool, active, label, badge, children, onClick }: {
  tool: Tool;
  active: boolean;
  label: string;
  badge?: number;
  children: ReactNode;
  onClick: () => void;
}) {
  return <button
    className={`cockpit-tool-button${active ? " active" : ""}`}
    type="button"
    aria-label={label}
    aria-controls={`overview-${tool}-panel`}
    aria-expanded={active}
    title={label}
    onClick={onClick}
  >
    {children}
    {badge !== undefined && badge > 0 && <span className="tool-badge">{badge > 99 ? "99+" : badge}</span>}
  </button>;
}

export function OverviewToolDock() {
  const [activeTool, setActiveTool] = useState<Tool | null>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  const robotCount = useFactoryStore((state) => Object.keys(state.robots).length);
  const alertCount = useFactoryStore((state) => state.alerts.length);

  useEffect(() => {
    if (!activeTool) return;
    function closeOnPointerDown(event: PointerEvent) {
      if (!dockRef.current?.contains(event.target as Node)) setActiveTool(null);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setActiveTool(null);
    }
    document.addEventListener("pointerdown", closeOnPointerDown);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnPointerDown);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [activeTool]);

  function toggle(tool: Tool) {
    setActiveTool((current) => current === tool ? null : tool);
  }

  return <div className="overview-tool-dock" ref={dockRef}>
    <div className="cockpit-tool-buttons" role="toolbar" aria-label="Operations panels">
      <LivePauseButton cockpit/>
      <ToolButton tool="metrics" active={activeTool === "metrics"} label="Open operations statistics" onClick={() => toggle("metrics")}><MetricsIcon/></ToolButton>
      <ToolButton tool="fleet" active={activeTool === "fleet"} label="Open fleet" badge={robotCount} onClick={() => toggle("fleet")}><RobotIcon/></ToolButton>
      <ToolButton tool="alerts" active={activeTool === "alerts"} label="Open alerts" badge={alertCount} onClick={() => toggle("alerts")}><AlertIcon/></ToolButton>
    </div>
    <DataFreshnessIndicator cockpit/>

    {activeTool === "metrics" && <section className="overview-popup metrics-popup" id="overview-metrics-panel" role="dialog" aria-labelledby="overview-metrics-title">
      <div className="overview-popup-head"><div><span>Live operations</span><h2 id="overview-metrics-title">Statistics</h2></div><button type="button" aria-label="Close statistics" onClick={() => setActiveTool(null)}>×</button></div>
      <div className="overview-popup-scroll">
        <KpiGrid/>
        <div className="popup-chart-head"><strong>Operations trend</strong><span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span></div>
        <OperationsChart/>
      </div>
    </section>}

    {activeTool === "fleet" && <section className="overview-popup" id="overview-fleet-panel" role="dialog" aria-labelledby="overview-fleet-title">
      <div className="overview-popup-head"><div><span>Realtime telemetry</span><h2 id="overview-fleet-title">Fleet · {robotCount}</h2></div><button type="button" aria-label="Close fleet" onClick={() => setActiveTool(null)}>×</button></div>
      <div className="overview-popup-scroll"><FleetTable compact/></div>
    </section>}

    {activeTool === "alerts" && <section className="overview-popup" id="overview-alerts-panel" role="dialog" aria-labelledby="overview-alerts-title">
      <div className="overview-popup-head"><div><span>Event stream</span><h2 id="overview-alerts-title">Recent alerts · {alertCount}</h2></div><button type="button" aria-label="Close alerts" onClick={() => setActiveTool(null)}>×</button></div>
      <div className="overview-popup-scroll"><AlertList/></div>
    </section>}
  </div>;
}
