"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ScenarioComparison,
  ScenarioStatusBadge,
} from "@/components/scenarios/scenario-comparison";
import { apiClient } from "@/lib/api-client";
import {
  scenarioRunRequestSchema,
  type Scenario,
  type ScenarioRunRequest,
} from "@/schemas/scenario";

type FieldErrors = Partial<Record<keyof ScenarioRunRequest, string>>;
type Action = "run" | "approve" | "reject" | "apply";

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

export default function ScenariosPage() {
  const router = useRouter();
  const [baseline, setBaseline] = useState<Scenario | null>(null);
  const [candidate, setCandidate] = useState<Scenario | null>(null);
  const [baselineState, setBaselineState] = useState<"loading" | "ready" | "error">("loading");
  const [resultState, setResultState] = useState<"empty" | "loading" | "ready" | "error">("empty");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<Action | null>(null);

  const loadBaseline = useCallback(async () => {
    setBaselineState("loading");
    setActionError(null);
    try {
      setBaseline(await apiClient.getBaselineScenario());
      setBaselineState("ready");
    } catch (error) {
      setActionError(`Unable to load baseline: ${message(error)}`);
      setBaselineState("error");
    }
  }, []);

  useEffect(() => { void loadBaseline(); }, [loadBaseline]);

  async function runScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
    setResultState("loading");
    setCandidate(null);
    try {
      setCandidate(await apiClient.runScenario(parsed.data));
      setResultState("ready");
    } catch (error) {
      setActionError(message(error));
      setResultState("error");
    } finally {
      setActiveAction(null);
    }
  }

  async function review(action: "approve" | "reject") {
    if (!candidate) return;
    setActionError(null);
    setActiveAction(action);
    try {
      const updated = action === "approve"
        ? await apiClient.approveScenario(candidate.id)
        : await apiClient.rejectScenario(candidate.id);
      setCandidate(updated);
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function applyScenario() {
    if (!candidate || candidate.status !== "APPROVED") return;
    const confirmed = window.confirm(
      "Apply this scenario? The realtime mock factory will reset and current tasks will be cleared.",
    );
    if (!confirmed) return;

    setActionError(null);
    setActiveAction("apply");
    try {
      setCandidate(await apiClient.applyScenario(candidate.id));
      router.push("/factory");
    } catch (error) {
      setActionError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  const busy = activeAction !== null;
  const canReview = candidate?.status === "SIMULATED";
  const canApply = candidate?.status === "APPROVED";

  return (
    <>
      <header className="page-head">
        <div>
          <h2>Scenario sandbox</h2>
          <p>Benchmark a candidate, review its KPI impact, then approve it before applying.</p>
        </div>
      </header>

      <div className="scenario-layout">
        <section className="panel">
          <div className="panel-head">
            <h3>Candidate configuration</h3>
            <span>SimPy benchmark</span>
          </div>
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
            <p className="form-help">
              Robot count maps to the realtime mock twin after approval. Travel/loading values are benchmark-only.
            </p>
            <div className="button-row">
              <button className="button" type="reset" disabled={busy}>Reset form</button>
              <button className="button primary" type="submit" disabled={busy}>
                {activeAction === "run" ? "Running…" : "Run benchmark"}
              </button>
            </div>
          </form>
        </section>

        <section className="panel scenario-result" aria-live="polite">
          <div className="panel-head">
            <h3>Review and approval</h3>
            {candidate ? <ScenarioStatusBadge status={candidate.status} /> : <span>No candidate</span>}
          </div>

          {actionError && <div className="scenario-error" role="alert">{actionError}</div>}

          {baselineState === "loading" && <div className="empty">Loading baseline…</div>}
          {baselineState === "error" && (
            <div className="empty">
              <p>Baseline is unavailable. You can retry without losing the form.</p>
              <button className="button" type="button" onClick={() => void loadBaseline()}>Retry baseline</button>
            </div>
          )}
          {resultState === "empty" && baselineState !== "loading" && (
            <div className="empty">Run a scenario to compare it with the baseline.</div>
          )}
          {resultState === "loading" && <div className="empty">Running discrete-event simulation…</div>}
          {resultState === "error" && <div className="empty">The benchmark did not complete. Check the error above and retry.</div>}

          {candidate && resultState === "ready" && (
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
                <div className="notice">Candidate is ready, but the baseline is unavailable for comparison.</div>
              )}
              <div className="review-note">
                Review the KPI differences before approving. Applying is blocked until approval.
              </div>
              <div className="button-row scenario-actions">
                <button
                  className="button danger"
                  type="button"
                  disabled={busy || !canReview}
                  onClick={() => void review("reject")}
                >
                  {activeAction === "reject" ? "Rejecting…" : "Reject"}
                </button>
                <button
                  className="button"
                  type="button"
                  disabled={busy || !canReview}
                  onClick={() => void review("approve")}
                >
                  {activeAction === "approve" ? "Approving…" : "Approve"}
                </button>
                <button
                  className="button primary"
                  type="button"
                  disabled={busy || !canApply}
                  onClick={() => void applyScenario()}
                >
                  {activeAction === "apply" ? "Applying…" : "Apply to factory"}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
