"use client";

import { AlertList } from "@/components/alerts/alert-list";
import {
  OperationsChart,
  OPERATIONS_TREND_LIVE_LABEL,
} from "@/components/charts/operations-chart";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { FactoryMap } from "@/components/factory/factory-map";
import { FleetTable } from "@/components/fleet/fleet-table";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

export default function Overview() {
  const robotCount = useFactoryStore((state) => Object.keys(state.robots).length);

  return <><header className="page-head"><div><h2>Operations overview</h2><p>Live state of the battery intralogistics simulation.</p></div>{usesMockData && <span className="notice">Development fixtures · not production data</span>}</header><KpiGrid/><div className="grid main-grid"><section className="panel"><div className="panel-head"><h3>Factory twin</h3><span>120 × 40 m · realtime 3D</span></div><FactoryMap/></section><div className="stack"><section className="panel"><div className="panel-head"><h3>Fleet</h3><span>{robotCount} {robotCount === 1 ? "AMR" : "AMRs"}</span></div><FleetTable compact/></section><section className="panel"><div className="panel-head"><h3>Recent alerts</h3><span>Persistent log</span></div><div className="panel-body"><AlertList limit={3}/></div></section></div><section className="panel"><div className="panel-head"><h3>Operations trend</h3><span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span></div><OperationsChart/></section></div><RobotDrawer/></>;
}
