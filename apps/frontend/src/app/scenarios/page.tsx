"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
import { LayoutComparison } from "@/components/scenarios/layout-comparison";
import {
  ScenarioRunForm,
  type ScenarioFieldErrors,
} from "@/components/scenarios/scenario-run-form";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import {
  QUEUE_KEYS,
  QUEUE_LABELS,
  filterQueue,
  isQueueKey,
  latestCommandForScenario,
  newestFirst,
  type QueueKey,
} from "@/lib/workflow";
import { useFactoryStore } from "@/stores/factory-store";
import { toastSuccess, toastError, toastInfo } from "@/stores/toast-store";
import type { LayoutSummary, LayoutVersion } from "@/schemas/layout";
import {
  scenarioRunRequestSchema,
  type Scenario,
  type ScenarioRunRequest,
} from "@/schemas/scenario";

type LoadState = "loading" | "ready" | "error";

function message(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

function newestUsefulScenario(scenarios: Scenario[]) {
  const ordered = newestFirst(scenarios);
  return ordered.find((scenario) => scenario.status === "SUBMITTED")
    ?? ordered.find((scenario) => scenario.status === "SIMULATED")
    ?? ordered.find((scenario) => scenario.status === "APPROVED")
    ?? ordered[0]
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
        {scenario.revision_of && <div><dt>Revision of</dt><dd>{scenario.revision_of}</dd></div>}
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
  const [candidate, setCandidate] = useState<Scenario | null>(null);
  const [revisionSource, setRevisionSource] = useState<Scenario | null>(null);
  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [selectedLayout, setSelectedLayout] = useState<LayoutVersion | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [queue, setQueue] = useState<QueueKey>("all");
  const [fieldErrors, setFieldErrors] = useState<ScenarioFieldErrors>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [commandLoadError, setCommandLoadError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<ScenarioAction | null>(null);
  const [applyConfirmationOpen, setApplyConfirmationOpen] = useState(false);
  const scenarios = useFactoryStore((state) => state.scenarios);
  const commands = useFactoryStore((state) => state.commands);
  const setScenarios = useFactoryStore((state) => state.setScenarios);
  const setCommands = useFactoryStore((state) => state.setCommands);
  const updateScenario = useFactoryStore((state) => state.updateScenario);
  const updateCommand = useFactoryStore((state) => state.updateCommand);
  const candidateCommand = useMemo(() => latestCommandForScenario(
    Object.values(commands),
    candidate?.id,
  ), [candidate?.id, commands]);

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
    return loaded;
  }, [setScenarios]);

  const loadCommands = useCallback(async () => {
    setCommandLoadError(null);
    try {
      setCommands(await apiClient.getCommands());
    } catch (error) {
      setCommandLoadError(`Command history is unavailable: ${message(error)}`);
    }
  }, [setCommands]);

  const loadPage = useCallback(async () => {
    setLoadState("loading");
    setActionError(null);
    try {
      const [loadedBaseline, loadedLayouts, loadedScenarios] = await Promise.all([
        apiClient.getBaselineScenario(),
        apiClient.getLayouts(),
        loadScenarios(),
        loadCommands(),
      ]);
      setBaseline(loadedBaseline);
      setLayouts(loadedLayouts);
      const query = new URLSearchParams(window.location.search);
      const requestedQueue = query.get("queue");
      if (isQueueKey(requestedQueue)) setQueue(requestedQueue);
      const requestedCandidate = query.get("candidate");
      const linkedCandidate = loadedScenarios.find((scenario) => scenario.id === requestedCandidate);
      if (linkedCandidate) setCandidate(linkedCandidate);
      const requestedId = query.get("layout");
      const requestedVersion = Number(query.get("version"));
      const requested = loadedLayouts.find((layout) => layout.id === requestedId);
      const initial = requested ?? loadedLayouts[0];
      if (initial) {
        setSelectedLayout(
          requested && Number.isInteger(requestedVersion) && requestedVersion > 0
            ? await apiClient.getLayoutVersion(requested.id, requestedVersion)
            : await apiClient.getLayout(initial.id),
        );
      }
      setLoadState("ready");
    } catch (error) {
      setActionError(`Unable to load scenarios: ${message(error)}`);
      setLoadState("error");
    }
  }, [loadCommands, loadScenarios]);

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
    if (candidateCommand?.status === "COMPLETED") void loadScenarios();
  }, [candidateCommand?.status, loadScenarios]);

  if (!user) return null;
  const currentUserId = user.id;
  const mayRun = can(user.role, "scenarios:run");
  const mayReview = can(user.role, "scenarios:review");
  const mayApply = can(user.role, "scenarios:apply");
  const mayViewLayout = can(user.role, "layout:view");
  const visibleScenarios = newestFirst(filterQueue(scenarios, queue, user.id));

  async function runScenario(request: ScenarioRunRequest) {
    if (!mayRun) {
      setActionError("Your role cannot run scenarios.");
      return;
    }

    const parsed = scenarioRunRequestSchema.safeParse(request);
    if (!parsed.success) {
      const errors: ScenarioFieldErrors = {};
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
      updateScenario(created);
      setCandidate(created);
      setRevisionSource(null);
      toastSuccess(
        `Scenario "${created.name}" simulated · `
        + `${created.metrics.throughput_per_hour.toFixed(1)} tasks/h · `
        + `${created.metrics.average_cycle_time.toFixed(1)}s avg cycle · `
        + `${created.metrics.starvation_events} starvation`,
      );
    } catch (error) {
      setActionError(message(error));
      toastError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function approveScenario() {
    if (!candidate || candidate.status !== "SUBMITTED" || !mayReview) {
      setActionError("Only a Monitor can review a submitted scenario.");
      return;
    }
    setActionError(null);
    setActiveAction("approve");
    try {
      const updated = await apiClient.approveScenario(candidate.id);
      setCandidate(updated);
      updateScenario(updated);
      toastSuccess("Scenario approved");
    } catch (error) {
      setActionError(message(error));
      toastError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function requestRevision(note: string) {
    if (!candidate || candidate.status !== "SUBMITTED" || !mayReview) {
      setActionError("Only a Monitor can request changes to a submitted scenario.");
      return;
    }
    setActionError(null);
    setActiveAction("request-revision");
    try {
      const updated = await apiClient.requestScenarioRevision(candidate.id, { note });
      setCandidate(updated);
      updateScenario(updated);
      toastSuccess("Revision requested");
    } catch (error) {
      setActionError(message(error));
      toastError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  async function startRevision() {
    if (
      !candidate
      || candidate.status !== "REVISION_REQUESTED"
      || candidate.created_by !== currentUserId
      || !mayRun
    ) {
      setActionError("Only the original Designer can revise this scenario.");
      return;
    }
    setActionError(null);
    try {
      const layout = await apiClient.getLayoutVersion(
        candidate.config.layout_id,
        candidate.config.layout_version,
      );
      setSelectedLayout(layout);
      setRevisionSource(candidate);
      window.scrollTo({ top: 0, behavior: "smooth" });
      toastInfo("Revision prepared — edit configuration above");
    } catch (error) {
      setActionError(`Unable to prepare revision: ${message(error)}`);
      toastError(`Unable to prepare revision: ${message(error)}`);
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
      updateScenario(updated);
      toastSuccess("Scenario submitted for review");
    } catch (error) {
      setActionError(message(error));
      toastError(message(error));
    } finally {
      setActiveAction(null);
    }
  }

  function requestApplyScenario() {
    if (!candidate || candidate.status !== "APPROVED" || !mayApply) {
      setActionError("Only a Monitor can apply an approved scenario.");
      return;
    }
    setApplyConfirmationOpen(true);
  }

  async function applyScenario() {
    if (!candidate || candidate.status !== "APPROVED" || !mayApply) return;
    setApplyConfirmationOpen(false);
    setActionError(null);
    setActiveAction("apply");
    try {
      const createdCommand = await apiClient.applyScenario(candidate.id, {
        timeout_seconds: 30,
        max_retries: 1,
      });
      updateCommand(createdCommand);
      toastInfo(`Apply command queued for "${candidate.name}"`);
    } catch (error) {
      setActionError(message(error));
      toastError(message(error));
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
        <div className="panel-head">
          <h3>Scenario history</h3>
          <span>{visibleScenarios.length} of {scenarios.length} saved in backend</span>
        </div>
        {scenarios.length > 0 && (
          <div className="toolbar queue-filters" role="group" aria-label="Candidate queue">
            {QUEUE_KEYS.map((key) => (
              <button
                key={key}
                className={`filter${queue === key ? " active" : ""}`}
                type="button"
                aria-pressed={queue === key}
                onClick={() => setQueue(key)}
              >
                {QUEUE_LABELS[key]} {filterQueue(scenarios, key, user.id).length}
              </button>
            ))}
          </div>
        )}
        {loadState === "loading" && <div className="empty">Loading scenario history…</div>}
        {loadState === "error" && <div className="empty">Scenario history is unavailable. Retry when the API is online.</div>}
        {loadState === "ready" && scenarios.length === 0 && <div className="empty">No candidate has been simulated yet.</div>}
        {scenarios.length > 0 && visibleScenarios.length === 0 && (
          <div className="empty">No candidate is in the {QUEUE_LABELS[queue].toLowerCase()} queue.</div>
        )}
        {visibleScenarios.length > 0 && (
          <div className="scenario-tabs" role="list" aria-label="Scenario history">
            {visibleScenarios.map((scenario) => (
              <button
                key={scenario.id}
                className={candidate?.id === scenario.id ? "selected" : ""}
                type="button"
                onClick={() => {
                  setCandidate(scenario);
                  setRevisionSource(null);
                }}
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
            <ScenarioRunForm
              key={`${selectedLayout?.layout_id}-${selectedLayout?.version}-${revisionSource?.id ?? "new"}`}
              layouts={layouts}
              selectedLayout={selectedLayout}
              revisionSource={revisionSource}
              fieldErrors={fieldErrors}
              busy={activeAction !== null}
              running={activeAction === "run"}
              onSelectLayout={(layoutId) => void selectLayout(layoutId)}
              onSelectVersion={(version) => void selectLayoutVersion(version)}
              onRun={(request) => void runScenario(request)}
            />
          ) : <ReadOnlyConfiguration scenario={candidate} />}
        </section>

        <section className="panel scenario-result" aria-live="polite">
          <div className="panel-head">
            <h3>Benchmark result</h3>
            {candidate ? <ScenarioStatusBadge status={candidate.status} /> : <span>No candidate</span>}
          </div>
          {actionError && <div className="scenario-error" role="alert">{actionError}</div>}
          {commandLoadError && <div className="review-note" role="status">{commandLoadError}</div>}
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
              <WorkflowTimeline
                status={candidate.status}
                command={candidateCommand}
              />
              {candidate.status === "REVISION_REQUESTED" && (
                <div className="revision-feedback" role="status">
                  <strong>Monitor requested changes</strong>
                  <p>{candidate.review_note}</p>
                </div>
              )}
              {baseline ? (
                <ScenarioComparison baseline={baseline.metrics} candidate={candidate.metrics} />
              ) : (
                <div className="notice">Baseline is unavailable for comparison.</div>
              )}
              {mayViewLayout && <LayoutComparison candidate={candidate} />}
              <ScenarioProvenance scenario={candidate} />
              <ScenarioActions
                role={user.role}
                status={candidate.status}
                activeAction={activeAction}
                onSubmitScenario={() => void submitScenario()}
                onApprove={() => void approveScenario()}
                onRequestRevision={(note) => void requestRevision(note)}
                onStartRevision={() => void startRevision()}
                canStartRevision={candidate.created_by === user.id}
                onApply={requestApplyScenario}
              />
            </div>
          )}
        </section>
      </div>
      {mayRun && <OptimizationPanel key={`${selectedLayout?.layout_id}-${selectedLayout?.version}`}
        layouts={layouts} selectedLayout={selectedLayout}/>}
      <ConfirmDialog
        open={applyConfirmationOpen}
        title={`Apply "${candidate?.name ?? "scenario"}" to the factory?`}
        message={<>
          <p>A command will be queued for the Fleet Manager bridge.</p>
          <p>When the bridge completes it, factory runtime resets AMRs, tasks, alerts and metrics.</p>
        </>}
        confirmLabel="Apply to factory"
        variant="danger"
        onCancel={() => setApplyConfirmationOpen(false)}
        onConfirm={() => void applyScenario()}
      />
    </>
  );
}
