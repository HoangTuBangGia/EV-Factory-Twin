"use client";

import { type FormEvent, useState } from "react";
import { apiClient } from "@/lib/api-client";
import {
  optimizationCandidateCount,
  optimizationRequestSchema,
  type OptimizationResult,
} from "@/schemas/optimization";
import type { LayoutSummary, LayoutVersion } from "@/schemas/layout";

function numbers(value: FormDataEntryValue | null) {
  return String(value ?? "").split(",").map((item) => Number(item.trim()));
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

function values(value: FormDataEntryValue | null) {
  return String(value ?? "").split(",").map((item) => item.trim()).filter(Boolean);
}

function candidateCount(form: HTMLFormElement) {
  const data = new FormData(form);
  return optimizationCandidateCount({
    layouts: data.getAll("optimization_layouts"),
    route_ids: values(data.get("route_ids")),
    robot_counts: values(data.get("robot_counts")),
    robot_speeds_mps: values(data.get("robot_speeds_mps")),
    charger_counts: values(data.get("charger_counts")),
    demand_intervals: values(data.get("demand_intervals")),
  });
}

export function OptimizationPanel({
  layouts,
  selectedLayout,
}: {
  layouts: LayoutSummary[];
  selectedLayout: LayoutVersion | null;
}) {
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [candidates, setCandidates] = useState(layouts.length > 0 ? 8 : 0);

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const layoutIds = data.getAll("optimization_layouts").map(String);
    const request = optimizationRequestSchema.safeParse({
      name_prefix: String(data.get("name_prefix") ?? ""),
      layouts: layouts
        .filter((layout) => layoutIds.includes(layout.id))
        .map((layout) => ({ layout_id: layout.id, layout_version: layout.latest_version })),
      route_ids: String(data.get("route_ids") ?? "").split(",").map((item) => item.trim()),
      robot_counts: numbers(data.get("robot_counts")),
      robot_speeds_mps: numbers(data.get("robot_speeds_mps")),
      charger_counts: numbers(data.get("charger_counts")),
      demand_intervals: numbers(data.get("demand_intervals")),
      num_tasks: Number(data.get("optimization_tasks")),
      loading_time: Number(data.get("optimization_loading")),
      simulation_time: Number(data.get("optimization_duration")),
    });
    if (!request.success) {
      setError(request.error.issues[0]?.message ?? "Invalid optimization request.");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      setResult(await apiClient.runOptimization(request.data));
    } catch (cause) {
      setError(message(cause));
    } finally {
      setRunning(false);
    }
  }

  return <details className="panel scenario-queue optimization-workspace">
    <summary className="panel-head">
      <div><h3>Advanced · Optimize multiple options</h3>
        <small>Deterministic bounded search across layouts and operating assumptions.</small></div>
      <span>{candidates} combinations · maximum 64</span>
    </summary>
    <form className="panel-body" onSubmit={run}
      onChange={(event) => setCandidates(candidateCount(event.currentTarget))}>
      <div className="form-grid">
        <div className="field"><label htmlFor="optimization-prefix">Name prefix</label>
          <input id="optimization-prefix" name="name_prefix" defaultValue="flow-option"/></div>
        <div className="field"><label htmlFor="optimization-layouts">Layouts</label>
          <select id="optimization-layouts" name="optimization_layouts" multiple size={Math.min(4, Math.max(2, layouts.length))}
            defaultValue={selectedLayout ? [selectedLayout.layout_id] : layouts[0] ? [layouts[0].id] : []}>
            {layouts.map((layout) => <option key={layout.id} value={layout.id}>{layout.name} · v{layout.latest_version}</option>)}
          </select></div>
        <div className="field"><label htmlFor="optimization-routes">Route IDs</label>
          <input id="optimization-routes" name="route_ids"
            defaultValue={selectedLayout?.routes.find((route) => route.kind === "DELIVERY")?.id
              ?? "BATTERY_DELIVERY"}/></div>
        <div className="field"><label htmlFor="optimization-robots">Robot counts</label>
          <input id="optimization-robots" name="robot_counts" defaultValue="2,3"/></div>
        <div className="field"><label htmlFor="optimization-speeds">Robot speeds (m/s)</label>
          <input id="optimization-speeds" name="robot_speeds_mps" defaultValue="0.8,1"/></div>
        <div className="field"><label htmlFor="optimization-chargers">Charger counts</label>
          <input id="optimization-chargers" name="charger_counts" defaultValue="1,2"/></div>
        <div className="field"><label htmlFor="optimization-demand">Demand intervals (s)</label>
          <input id="optimization-demand" name="demand_intervals" defaultValue="5"/></div>
        <div className="field"><label htmlFor="optimization-tasks">Tasks</label>
          <input id="optimization-tasks" name="optimization_tasks" type="number" defaultValue="100"/></div>
        <div className="field"><label htmlFor="optimization-loading">Loading time (s)</label>
          <input id="optimization-loading" name="optimization_loading" type="number" defaultValue="5"/></div>
        <div className="field"><label htmlFor="optimization-duration">Simulation time (s)</label>
          <input id="optimization-duration" name="optimization_duration" type="number" defaultValue="3600"/></div>
      </div>
      <p className="form-help">
        Comma-separated values form a Cartesian product. Every route must exist in every selected
        layout. This is deterministic search, not an autonomous apply action.
      </p>
      <div className={`optimization-count${candidates > 64 ? " invalid" : ""}`} role="status">
        <strong>{candidates} candidate{candidates === 1 ? "" : "s"}</strong>
        <span>{candidates > 64 ? "Reduce the dimensions to 64 or fewer." : "Ready to evaluate within the bounded limit."}</span>
      </div>
      {error && <div className="scenario-error" role="alert">{error}</div>}
      <button className="button primary" type="submit"
        disabled={running || layouts.length === 0 || candidates === 0 || candidates > 64}>
        {running ? "Evaluating…" : "Evaluate candidates"}
      </button>
    </form>
    {result && <div className="table-wrap">
      <div className="review-note" role="status">
        Recommendation: <strong>{result.recommendation.name}</strong> from {result.evaluated_candidates} candidates
        <a className="button" href={`/scenarios?candidate=${encodeURIComponent(result.recommendation.id)}`}>
          Open recommended candidate
        </a>
      </div>
      <table className="data-table"><thead><tr>
        <th>Rank</th><th>Scenario</th><th>Robots</th><th>Speed</th><th>Chargers</th><th>Completion</th><th>Throughput</th>
      </tr></thead><tbody>{result.ranking.map(({ rank, scenario }) => <tr key={scenario.id}>
        <td>{rank}</td><td>{scenario.name}</td><td>{scenario.config.num_robots}</td>
        <td>{scenario.config.robot_speed_mps} m/s</td><td>{scenario.config.charger_count}</td>
        <td>{(scenario.metrics.completion_rate * 100).toFixed(1)}%</td>
        <td>{scenario.metrics.throughput_per_hour.toFixed(1)} tasks/h</td>
      </tr>)}</tbody></table>
    </div>}
  </details>;
}
