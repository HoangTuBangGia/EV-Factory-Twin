"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import {
  ScenarioActions,
  type ScenarioAction,
} from "@/components/scenarios/scenario-actions";
import {
  ScenarioComparison,
  ScenarioStatusBadge,
} from "@/components/scenarios/scenario-comparison";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
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
    num_robots: Number(data.get("num_robots")),
    num_tasks: Number(data.get("num_tasks")),
    task_arrival_interval: Number(data.get("task_arrival_interval")),
    travel_time: Number(data.get("travel_time")),
    loading_time: Number(data.get("loading_time")),
    simulation_time: Number(data.get("simulation_time")),
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
  return reversed.find((scenario) => scenario.status === "SIMULATED")
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
  const router = useRouter();
  const { user } = useAuth();
  const [baseline, setBaseline] = useState<Scenario | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [candidate, setCandidate] = useState<Scenario | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<ScenarioAction | null>(null);

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
      const [loadedBaseline] = await Promise.all([
        apiClient.getBaselineScenario(),
        loadScenarios(),
      ]);
      setBaseline(loadedBaseline);
      setLoadState("ready");
    } catch (error) {
      setActionError(`Unable to load scenarios: ${message(error)}`);
      setLoadState("error");
    }
  }, [loadScenarios]);

  useEffect(() => { void loadPage(); }, [loadPage]);

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
    if (!candidate || !mayReview) {
      setActionError("Your role cannot review scenarios.");
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

  async function applyScenario() {
    if (!candidate || candidate.status !== "APPROVED" || !mayApply) {
      setActionError("Only a Monitor can apply an approved scenario.");
      return;
    }
    if (!window.confirm(
      "Apply this scenario? The realtime mock factory will reset and current tasks will be cleared.",
    )) return;

    setActionError(null);
    setActiveAction("apply");
    try {
      const updated = await apiClient.applyScenario(candidate.id);
      setCandidate(updated);
      setScenarios((current) => upsertScenario(current, updated));
      router.push("/factory");
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
            <form className="panel-body" onSubmit={runScenario} noValidate>
              <div className="form-grid">
                <div className="field field-wide">
                  <label htmlFor="scenario-name">Scenario name</label>
                  <input id="scenario-name" name="name" defaultValue="candidate-01" required />
                  {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
                </div>
                <div className="field">
                  <label htmlFor="num-robots">Robot count</label>
                  <input id="num-robots" name="num_robots" type="number" min="1" max="10" defaultValue="5" />
                  {fieldErrors.num_robots && <span className="field-error">{fieldErrors.num_robots}</span>}
                </div>
                <div className="field">
                  <label htmlFor="num-tasks">Number of tasks</label>
                  <input id="num-tasks" name="num_tasks" type="number" min="1" max="10000" defaultValue="500" />
                  {fieldErrors.num_tasks && <span className="field-error">{fieldErrors.num_tasks}</span>}
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
              <p className="form-help">Robot count maps to the realtime mock twin after Monitor approval.</p>
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
                onReview={(action) => void review(action)}
                onApply={() => void applyScenario()}
              />
            </div>
          )}
        </section>
      </div>
    </>
  );
}
