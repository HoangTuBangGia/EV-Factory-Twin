import { OperationsChart, OPERATIONS_TREND_LIVE_LABEL } from "@/components/charts/operations-chart";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { usesMockData } from "@/lib/env";

export default function AnalyticsPage(){return <><header className="page-head"><div><h2>Analytics</h2><p>{usesMockData ? "Development KPI fixtures for local UI work." : "Live KPI history collected from WebSocket updates."}</p></div></header><KpiGrid/><div className="grid main-grid"><section className="panel"><div className="panel-head"><h3>Throughput trend</h3><span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span></div><OperationsChart mode="throughput"/></section><section className="panel"><div className="panel-head"><h3>Cycle-time trend</h3><span>{usesMockData ? "Fixture history" : OPERATIONS_TREND_LIVE_LABEL}</span></div><OperationsChart mode="cycle"/></section></div></>}
