"use client";

import { type FormEvent, useEffect, useState } from "react";
import type { LayoutSummary, LayoutVersion } from "@/schemas/layout";
import type { Scenario, ScenarioRunRequest } from "@/schemas/scenario";
import { toastInfo } from "@/stores/toast-store";

export const SIMULATION_SLOW_WARNING_MS = 60_000;

export function formatElapsedTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  return `${minutes}:${String(totalSeconds % 60).padStart(2, "0")}`;
}

export type ScenarioFieldErrors = Partial<Record<keyof ScenarioRunRequest, string>>;

export function scenarioDefaults(
  layout: LayoutVersion | null,
  revisionSource: Scenario | null = null,
): ScenarioRunRequest {
  if (revisionSource) {
    const routeId = layout?.routes.some((route) => route.id === revisionSource.config.route_id)
      ? revisionSource.config.route_id
      : layout?.routes.find((route) => route.kind === "DELIVERY")?.id
        ?? revisionSource.config.route_id;
    return {
      name: `${revisionSource.name}-revision`.slice(0, 80),
      ...revisionSource.config,
      layout_id: layout?.layout_id ?? revisionSource.config.layout_id,
      layout_version: layout?.version ?? revisionSource.config.layout_version,
      route_id: routeId,
      revision_of: revisionSource.id,
    };
  }
  return {
    name: "candidate-01",
    layout_id: layout?.layout_id ?? "",
    layout_version: layout?.version ?? 1,
    route_id: layout?.routes.find((route) => route.kind === "DELIVERY")?.id ?? "",
    num_robots: layout?.config.robot_count ?? 2,
    num_tasks: 500,
    task_arrival_interval: Math.min(60, Math.max(1, layout?.config.demand_interval_seconds ?? 5)),
    travel_time: 30,
    loading_time: 10,
    simulation_time: 3600,
    robot_speed_mps: layout?.config.robot_speed_mps ?? 1,
    charger_count: layout?.config.charger_count ?? 1,
  };
}

function readScenarioInput(form: HTMLFormElement): ScenarioRunRequest {
  const data = new FormData(form);
  const revisionOf = String(data.get("revision_of") ?? "");
  return {
    name: String(data.get("name") ?? ""),
    layout_id: String(data.get("layout_id") ?? ""),
    layout_version: Number(data.get("layout_version")),
    route_id: String(data.get("route_id") ?? ""),
    num_robots: Number(data.get("num_robots")),
    num_tasks: Number(data.get("num_tasks")),
    task_arrival_interval: Number(data.get("task_arrival_interval")),
    travel_time: Number(data.get("travel_time")),
    loading_time: Number(data.get("loading_time")),
    simulation_time: Number(data.get("simulation_time")),
    robot_speed_mps: Number(data.get("robot_speed_mps")),
    charger_count: Number(data.get("charger_count")),
    revision_of: revisionOf || undefined,
  };
}

function FieldError({ error }: { error?: string }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export function ScenarioRunForm({
  layouts,
  selectedLayout,
  revisionSource = null,
  fieldErrors,
  busy,
  running,
  onSelectLayout,
  onSelectVersion,
  onRun,
}: {
  layouts: LayoutSummary[];
  selectedLayout: LayoutVersion | null;
  revisionSource?: Scenario | null;
  fieldErrors: ScenarioFieldErrors;
  busy: boolean;
  running: boolean;
  onSelectLayout: (layoutId: string) => void;
  onSelectVersion: (version: number) => void;
  onRun: (request: ScenarioRunRequest) => void;
}) {
  const defaults = scenarioDefaults(selectedLayout, revisionSource);
  const [summary, setSummary] = useState(defaults);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!running) return;
    setElapsedSeconds(0);
    const timer = setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    const warning = setTimeout(() => {
      toastInfo("Simulation still running… Results will appear when the benchmark completes.");
    }, SIMULATION_SLOW_WARNING_MS);
    return () => {
      clearInterval(timer);
      clearTimeout(warning);
    };
  }, [running]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onRun(readScenarioInput(event.currentTarget));
  }

  return <form className="panel-body scenario-run-form" onSubmit={submit} noValidate
    onChange={(event) => setSummary(readScenarioInput(event.currentTarget))}
    onReset={() => setSummary(defaults)}>
    {defaults.revision_of && <input type="hidden" name="revision_of" value={defaults.revision_of}/>}
    {revisionSource && (
      <div className="revision-source" role="status">
        <strong>Revising {revisionSource.id}</strong>
        <span>{revisionSource.review_note}</span>
      </div>
    )}
    <div className="scenario-setting-heading">
      <strong>Basic settings</strong>
      <span>Choose the factory flow and simulation scale.</span>
    </div>
    <div className="form-grid">
      <div className="field field-wide">
        <label htmlFor="scenario-name">Scenario name</label>
        <input id="scenario-name" name="name" defaultValue={defaults.name} required />
        <FieldError error={fieldErrors.name}/>
      </div>
      <div className="field field-wide">
        <label htmlFor="scenario-layout">Layout</label>
        <select id="scenario-layout" name="layout_id" required
          value={selectedLayout?.layout_id ?? ""}
          onChange={(event) => onSelectLayout(event.target.value)}>
          <option value="" disabled>Select a layout</option>
          {layouts.map((layout) => <option value={layout.id} key={layout.id}>
            {layout.name} · v{layout.latest_version}
          </option>)}
        </select>
        <FieldError error={fieldErrors.layout_id}/>
      </div>
      <div className="field">
        <label htmlFor="scenario-layout-version">Layout version</label>
        <input id="scenario-layout-version" name="layout_version" type="number" min="1"
          max={layouts.find((layout) => layout.id === selectedLayout?.layout_id)?.latest_version}
          value={selectedLayout?.version ?? ""}
          onChange={(event) => onSelectVersion(Number(event.target.value))}/>
        <FieldError error={fieldErrors.layout_version}/>
      </div>
      <div className="field field-wide">
        <label htmlFor="scenario-route">Route</label>
        <select id="scenario-route" name="route_id" required disabled={!selectedLayout}
          defaultValue={defaults.route_id}>
          {selectedLayout?.routes.filter((route) => route.kind === "DELIVERY")
            .map((route) => <option value={route.id} key={route.id}>
            {route.id} · {route.start_station_id} → {route.end_station_id}
          </option>)}
        </select>
        <FieldError error={fieldErrors.route_id}/>
      </div>
      <div className="field">
        <label htmlFor="num-robots">Robot count</label>
        <input id="num-robots" name="num_robots" type="number" min="1" max="10"
          defaultValue={defaults.num_robots}/>
        <FieldError error={fieldErrors.num_robots}/>
      </div>
      <div className="field">
        <label htmlFor="num-tasks">Number of tasks</label>
        <input id="num-tasks" name="num_tasks" type="number" min="1" max="10000"
          defaultValue={defaults.num_tasks}/>
        <FieldError error={fieldErrors.num_tasks}/>
      </div>
      <div className="field">
        <label htmlFor="task-interval">Task arrival interval (s)</label>
        <input id="task-interval" name="task_arrival_interval" type="number" min="1" max="60"
          step="0.1" defaultValue={defaults.task_arrival_interval}/>
        <FieldError error={fieldErrors.task_arrival_interval}/>
      </div>
      <div className="field">
        <label htmlFor="simulation-time">Simulation time (s)</label>
        <input id="simulation-time" name="simulation_time" type="number" min="0.1" max="86400"
          step="0.1" defaultValue={defaults.simulation_time}/>
        <FieldError error={fieldErrors.simulation_time}/>
      </div>
    </div>

    <details className="scenario-advanced-settings">
      <summary>Advanced settings</summary>
      <p className="form-help">Tune vehicle and handling assumptions only when the layout defaults are not suitable.</p>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="robot-speed">Robot speed (m/s)</label>
          <input id="robot-speed" name="robot_speed_mps" type="number" min="0.1" max="10" step="0.1"
            defaultValue={defaults.robot_speed_mps}/>
          <FieldError error={fieldErrors.robot_speed_mps}/>
        </div>
        <div className="field">
          <label htmlFor="charger-count">Charger count</label>
          <input id="charger-count" name="charger_count" type="number" min="1" max="20"
            defaultValue={defaults.charger_count}/>
          <FieldError error={fieldErrors.charger_count}/>
        </div>
        <div className="field">
          <label htmlFor="travel-time">Travel time (s)</label>
          <input id="travel-time" name="travel_time" type="number" min="0.1" max="86400" step="0.1"
            defaultValue={defaults.travel_time}/>
          <FieldError error={fieldErrors.travel_time}/>
        </div>
        <div className="field">
          <label htmlFor="loading-time">Loading time (s)</label>
          <input id="loading-time" name="loading_time" type="number" min="0.1" max="86400" step="0.1"
            defaultValue={defaults.loading_time}/>
          <FieldError error={fieldErrors.loading_time}/>
        </div>
      </div>
    </details>

    <div className="scenario-run-summary" aria-label="Simulation summary">
      <strong>{summary.num_robots} AMRs</strong>
      <span>{summary.route_id || "No route"}</span>
      <span>Demand every {summary.task_arrival_interval}s</span>
      <span>Simulate {summary.simulation_time}s</span>
    </div>
    <p className="form-help">Route distance and congestion are resolved authoritatively from the immutable layout version.</p>
    {running && (
      <div className="simulation-progress">
        <div className="simulation-progress-head">
          <span>Simulation in progress</span>
          <strong role="timer">{formatElapsedTime(elapsedSeconds)}</strong>
        </div>
        <div
          className="simulation-progress-track"
          role="progressbar"
          aria-label="Simulation running"
          aria-valuetext={`Elapsed ${elapsedSeconds} seconds`}
        ><i/></div>
        <span id="simulation-cancel-help" className="sr-only">Cannot cancel mid-run.</span>
      </div>
    )}
    <div className="button-row">
      <button className="button" type="reset" disabled={busy}>Reset to layout defaults</button>
      {running && (
        <button
          className="button"
          type="button"
          disabled
          title="Cannot cancel mid-run"
          aria-describedby="simulation-cancel-help"
        >Cancel</button>
      )}
      <button className="button primary" type="submit" disabled={busy}>
        {running ? "Running…" : "Run benchmark"}
      </button>
    </div>
  </form>;
}
