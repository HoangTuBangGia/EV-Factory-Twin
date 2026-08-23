"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import {
  ScenarioActions,
  type ScenarioAction,
} from "@/components/scenarios/scenario-actions";
import {
  ScenarioComparison,
  ScenarioStatusBadge,
} from "@/components/scenarios/scenario-comparison";
import { OptimizationPanel } from "@/components/scenarios/optimization-panel";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import { useFactoryStore } from "@/stores/factory-store";
import type { LayoutSummary, LayoutVersion } from "@/schemas/layout";
import {
  scenarioRunRequestSchema,
  type Scenario,
  type ScenarioRunRequest,
} from "@/schemas/scenario";

type FieldErrors = Partial<Record<keyof ScenarioRunRequest, string>>;
type LoadState = "loading" | "ready" | "error";

function readScenarioInput(form: HTMLFormElement): ScenarioRunRequest {
  const data = new FormData(form);
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
  };
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

function upsertScenario(scenarios: Scenario[], updated: Scenario) {
  const exists = scenarios.some((scenario) => scenario.id === updated.id);
  return exists
    ? scenarios.map((scenario) => scenario.id === updated.id ? updated : scenario)
    : [...scenarios, updated];
}

function newestUsefulScenario(scenarios: Scenario[]) {
  const reversed = [...scenarios].reverse();
  return reversed.find((scenario) => scenario.status === "SUBMITTED")
    ?? reversed.find((scenario) => scenario.status === "SIMULATED")
    ?? reversed.find((scenario) => scenario.status === "APPROVED")
    ?? reversed[0]
    ?? null;
}

function workflowTimestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not yet";
}

function workflowActor(value: string | null) {
  return value ?? "System baseline";
}

function ScenarioProvenance({ scenario }: { scenario: Scenario }) {
  return (
    <details className="scenario-provenance">
      <summary>Workflow provenance · version {scenario.version}</summary>
      <dl>
        <div><dt>Created</dt><dd>{workflowTimestamp(scenario.created_at)}<small>{workflowActor(scenario.created_by)}</small></dd></div>
        <div><dt>Reviewed</dt><dd>{workflowTimestamp(scenario.reviewed_at)}<small>{workflowActor(scenario.reviewed_by)}</small></dd></div>
        <div><dt>Applied</dt><dd>{workflowTimestamp(scenario.applied_at)}<small>{workflowActor(scenario.applied_by)}</small></dd></div>
      </dl>
    </details>
  );
}

function ReadOnlyConfiguration({ scenario }: { scenario: Scenario | null }) {
  if (!scenario) {
    return <div className="empty">No scenario is available for review.</div>;
  }

  const values = [
    ["Robot count", scenario.config.num_robots],
    ["Layout", `${scenario.config.layout_id} · v${scenario.config.layout_version}`],
    ["Route", scenario.config.route_id],
    ["Robot speed", `${scenario.config.robot_speed_mps} m/s`],
    ["Chargers", scenario.config.charger_count],
    ["Tasks", scenario.config.num_tasks],
    ["Arrival interval", `${scenario.config.task_arrival_interval} s`],
    ["Travel time", `${scenario.config.travel_time} s`],
    ["Loading time", `${scenario.config.loading_time} s`],
    ["Simulation time", `${scenario.config.simulation_time} s`],
  ];

  return (
    <div className="panel-body">
      <div className="readonly-config">
        {values.map(([label, value]) => (
          <div key={label}><small>{label}</small><strong>{value}</strong></div>
        ))}
      </div>
      <p className="form-help">Configuration is read-only for this role.</p>
    </div>
  );
}

export default function ScenariosPage() {
  const { user } = useAuth();
  const [baseline, setBaseline] = useState<Scenario | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [candidate, setCandidate] = useState<Scenario | null>(null);
  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [selectedLayout, setSelectedLayout] = useState<LayoutVersion | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<ScenarioAction | null>(null);
  const [operationId, setOperationId] = useState<string | null>(null);
  const command = useFactoryStore((state) => operationId ? state.commands[operationId] : null);
  const updateCommand = useFactoryStore((state) => state.updateCommand);

  const loadScenarios = useCallback(async () => {
    const loaded = await apiClient.getScenarios();
    setScenarios(loaded);
    setCandidate((current) => {
      if (current) {
        const refreshed = loaded.find((scenario) => scenario.id === current.id);
        if (refreshed) return refreshed;
      }
      return newestUsefulScenario(loaded);
    });
  }, []);

  const loadPage = useCallback(async () => {
    setLoadState("loading");
    setActionError(null);
    try {
      const [loadedBaseline, loadedLayouts] = await Promise.all([
        apiClient.getBaselineScenario(),
        apiClient.getLayouts(),
        loadScenarios(),
      ]);
      setBaseline(loadedBaseline);
      setLayouts(loadedLayouts);
      if (loadedLayouts[0]) {
        setSelectedLayout(await apiClient.getLayout(loadedLayouts[0].id));
      }
      setLoadState("ready");
    } catch (error) {
      setActionError(`Unable to load scenarios: ${message(error)}`);
      setLoadState("error");
    }
  }, [loadScenarios]);

  async function selectLayout(layoutId: string) {
    setActionError(null);
    try {
      setSelectedLayout(await apiClient.getLayout(layoutId));
    } catch (error) {
      setActionError(`Unable to load layout: ${message(error)}`);
    }
  }

  async function selectLayoutVersion(version: number) {
    if (!selectedLayout || !Number.isInteger(version) || version < 1) return;
    setActionError(null);
    try {
      setSelectedLayout(await apiClient.getLayoutVersion(selectedLayout.layout_id, version));
    } catch (error) {
      setActionError(`Unable to load layout version: ${message(error)}`);
    }
  }

  useEffect(() => { void loadPage(); }, [loadPage]);

  useEffect(() => {
    if (command?.status === "COMPLETED") void loadScenarios();
  }, [command?.status, loadScenarios]);

  if (!user) return null;
  const mayRun = can(user.role, "scenarios:run");
  const mayReview = can(user.role, "scenarios:review");
  const mayApply = can(user.role, "scenarios:apply");

  async function runScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mayRun) {
      setActionError("Your role cannot run scenarios.");
      return;
    }

    const parsed = scenarioRunRequestSchema.safeParse(readScenarioInput(event.currentTarget));
    if (!parsed.success) {
      const errors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const field = issue.path[0] as keyof ScenarioRunRequest | undefined;
        if (field && !errors[field]) errors[field] = issue.message;
      }
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
    setActionError(null);
    setActiveAction("run");
    try {
      const created = await apiClient.runScenario(parsed.data);
      setScenarios((current) => upsertScenario(current, created));
      setCandidate(created);
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function review(action: "approve" | "reject") {
    if (!candidate || candidate.status !== "SUBMITTED" || !mayReview) {
      setActionError("Only a Monitor can review a submitted scenario.");
      return;
    }
    setActionError(null);
    setActiveAction(action);
    try {
      const updated = action === "approve"
        ? await apiClient.approveScenario(candidate.id)
        : await apiClient.rejectScenario(candidate.id);
      setCandidate(updated);
      setScenarios((current) => upsertScenario(current, updated));
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function submitScenario() {
    if (!candidate || candidate.status !== "SIMULATED" || !mayRun) {
      setActionError("Only a Designer can submit a simulated scenario.");
      return;
    }
    setActionError(null);
    setActiveAction("submit");
    try {
      const updated = await apiClient.submitScenario(candidate.id);
      setCandidate(updated);
      setScenarios((current) => upsertScenario(current, updated));
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function applyScenario() {
    if (!candidate || candidate.status !== "APPROVED" || !mayApply) {
      setActionError("Only a Monitor can apply an approved scenario.");
      return;
    }
    if (!window.confirm(
      "Apply this scenario? A command will be sent to the simulation Fleet Manager.",
    )) return;

    setActionError(null);
    setActiveAction("apply");
    try {
      const createdCommand = await apiClient.applyScenario(candidate.id, {
        timeout_seconds: 30,
        max_retries: 1,
      });
      updateCommand(createdCommand);
      setOperationId(createdCommand.operation_id);
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h2>Scenario sandbox</h2>
          <p>Designer simulations require an independent Monitor review before apply.</p>
        </div>
        <button className="button" type="button" disabled={loadState === "loading"} onClick={() => void loadPage()}>
          {loadState === "loading" ? "Refreshing…" : "Refresh scenarios"}
        </button>
      </header>

      <section className="panel scenario-queue">
        <div className="panel-head"><h3>Scenario history</h3><span>{scenarios.length} saved in backend</span></div>
        {loadState === "loading" && <div className="empty">Loading scenario history…</div>}
        {loadState === "error" && <div className="empty">Scenario history is unavailable. Retry when the API is online.</div>}
        {loadState === "ready" && scenarios.length === 0 && <div className="empty">No candidate has been simulated yet.</div>}
        {scenarios.length > 0 && (
          <div className="scenario-tabs" role="list" aria-label="Scenario history">
            {[...scenarios].reverse().map((scenario) => (
              <button
                key={scenario.id}
                className={candidate?.id === scenario.id ? "selected" : ""}
                type="button"
                onClick={() => setCandidate(scenario)}
              >
                <span>{scenario.name}</span>
                <small>{scenario.id} · {scenario.status}</small>
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="scenario-layout">
        <section className="panel">
          <div className="panel-head">
            <h3>{mayRun ? "Candidate configuration" : "Selected configuration"}</h3>
            <span>{mayRun ? "Designer · SimPy benchmark" : `${user.role} · Read only`}</span>
          </div>
          {mayRun ? (
            <form key={`${selectedLayout?.layout_id}-${selectedLayout?.version}`}
              className="panel-body" onSubmit={runScenario} noValidate>
              <div className="form-grid">
                <div className="field field-wide">
                  <label htmlFor="scenario-name">Scenario name</label>
                  <input id="scenario-name" name="name" defaultValue="candidate-01" required />
                  {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
                </div>
                <div className="field field-wide">
                  <label htmlFor="scenario-layout">Layout</label>
                  <select id="scenario-layout" name="layout_id" required
                    value={selectedLayout?.layout_id ?? ""}
                    onChange={(event) => void selectLayout(event.target.value)}>
                    <option value="" disabled>Select a layout</option>
                    {layouts.map((layout) => <option value={layout.id} key={layout.id}>
                      {layout.name} · v{layout.latest_version}
                    </option>)}
                  </select>
                  {fieldErrors.layout_id && <span className="field-error">{fieldErrors.layout_id}</span>}
                </div>
                <div className="field">
                  <label htmlFor="scenario-layout-version">Layout version</label>
                  <input id="scenario-layout-version" name="layout_version" type="number" min="1"
                    max={layouts.find((layout) => layout.id === selectedLayout?.layout_id)?.latest_version}
                    value={selectedLayout?.version ?? ""}
                    onChange={(event) => void selectLayoutVersion(Number(event.target.value))}/>
                  {fieldErrors.layout_version && <span className="field-error">{fieldErrors.layout_version}</span>}
                </div>
                <div className="field field-wide">
                  <label htmlFor="scenario-route">Route</label>
                  <select id="scenario-route" name="route_id" required disabled={!selectedLayout}>
                    {selectedLayout?.routes.map((route) => <option value={route.id} key={route.id}>
                      {route.id} · {route.start_station_id} → {route.end_station_id}
                    </option>)}
                  </select>
                  {fieldErrors.route_id && <span className="field-error">{fieldErrors.route_id}</span>}
                </div>
                <div className="field">
                  <label htmlFor="num-robots">Robot count</label>
                  <input id="num-robots" name="num_robots" type="number" min="1" max="10" defaultValue={selectedLayout?.config.robot_count ?? 2} />
                  {fieldErrors.num_robots && <span className="field-error">{fieldErrors.num_robots}</span>}
                </div>
                <div className="field">
                  <label htmlFor="num-tasks">Number of tasks</label>
                  <input id="num-tasks" name="num_tasks" type="number" min="1" max="10000" defaultValue="500" />
                  {fieldErrors.num_tasks && <span className="field-error">{fieldErrors.num_tasks}</span>}
                </div>
                <div className="field">
                  <label htmlFor="robot-speed">Robot speed (m/s)</label>
                  <input id="robot-speed" name="robot_speed_mps" type="number" min="0.1" max="10" step="0.1"
                    defaultValue={selectedLayout?.config.robot_speed_mps ?? 1}/>
                  {fieldErrors.robot_speed_mps && <span className="field-error">{fieldErrors.robot_speed_mps}</span>}
                </div>
                <div className="field">
                  <label htmlFor="charger-count">Charger count</label>
                  <input id="charger-count" name="charger_count" type="number" min="1" max="20"
                    defaultValue={selectedLayout?.config.charger_count ?? 1}/>
                  {fieldErrors.charger_count && <span className="field-error">{fieldErrors.charger_count}</span>}
                </div>
                <div className="field">
                  <label htmlFor="task-interval">Task arrival interval (s)</label>
                  <input id="task-interval" name="task_arrival_interval" type="number" min="1" max="60" step="0.1" defaultValue="5" />
                  {fieldErrors.task_arrival_interval && <span className="field-error">{fieldErrors.task_arrival_interval}</span>}
                </div>
                <div className="field">
                  <label htmlFor="travel-time">Travel time (s)</label>
                  <input id="travel-time" name="travel_time" type="number" min="0.1" max="86400" step="0.1" defaultValue="30" />
                  {fieldErrors.travel_time && <span className="field-error">{fieldErrors.travel_time}</span>}
                </div>
                <div className="field">
                  <label htmlFor="loading-time">Loading time (s)</label>
                  <input id="loading-time" name="loading_time" type="number" min="0.1" max="86400" step="0.1" defaultValue="10" />
                  {fieldErrors.loading_time && <span className="field-error">{fieldErrors.loading_time}</span>}
                </div>
                <div className="field">
                  <label htmlFor="simulation-time">Simulation time (s)</label>
                  <input id="simulation-time" name="simulation_time" type="number" min="0.1" max="86400" step="0.1" defaultValue="3600" />
                  {fieldErrors.simulation_time && <span className="field-error">{fieldErrors.simulation_time}</span>}
                </div>
              </div>
              <p className="form-help">Route distance and congestion are resolved authoritatively from the immutable layout version.</p>
              <div className="button-row">
                <button className="button" type="reset" disabled={activeAction !== null}>Reset form</button>
                <button className="button primary" type="submit" disabled={activeAction !== null}>
                  {activeAction === "run" ? "Running…" : "Run benchmark"}
                </button>
              </div>
            </form>
          ) : <ReadOnlyConfiguration scenario={candidate} />}
        </section>

        <section className="panel scenario-result" aria-live="polite">
          <div className="panel-head">
            <h3>Benchmark result</h3>
            {candidate ? <ScenarioStatusBadge status={candidate.status} /> : <span>No candidate</span>}
          </div>
          {actionError && <div className="scenario-error" role="alert">{actionError}</div>}
          {!candidate && loadState !== "loading" && (
            <div className="empty">{mayRun ? "Run a scenario to compare it with the baseline." : "Wait for a Designer to run a scenario."}</div>
          )}
          {candidate && (
            <div className="scenario-review">
              <div className="scenario-summary">
                <div><small>Scenario</small><strong>{candidate.name}</strong></div>
                <div><small>Scenario ID</small><strong>{candidate.id}</strong></div>
                <div><small>Completed</small><strong>{candidate.metrics.completed_tasks}</strong></div>
                <div><small>Benchmark time</small><strong>{candidate.duration_ms.toFixed(1)} ms</strong></div>
              </div>
              {baseline ? (
                <ScenarioComparison baseline={baseline.metrics} candidate={candidate.metrics} />
              ) : (
                <div className="notice">Baseline is unavailable for comparison.</div>
              )}
              <ScenarioProvenance scenario={candidate} />
              <ScenarioActions
                role={user.role}
                status={candidate.status}
                activeAction={activeAction}
                onSubmitScenario={() => void submitScenario()}
                onReview={(action) => void review(action)}
                onApply={() => void applyScenario()}
              />
              {command && <div className="review-note" role="status">
                Command <strong>{command.operation_id}</strong> · {command.status}
              </div>}
            </div>
          )}
        </section>
      </div>
      {mayRun && <OptimizationPanel key={`${selectedLayout?.layout_id}-${selectedLayout?.version}`}
        layouts={layouts} selectedLayout={selectedLayout}/>}
    </>
  );
}
