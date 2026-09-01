import {
  APPLY_PHASES,
  WORKFLOW_STAGES,
  applyProgress,
  stageState,
  type WorkflowStage,
} from "@/lib/workflow";
import type { Command } from "@/schemas/command";
import type { ScenarioStatus } from "@/schemas/scenario";

const STAGE_LABELS: Readonly<Record<WorkflowStage, string>> = {
  SIMULATED: "Simulated",
  SUBMITTED: "Submitted",
  APPROVED: "Approved",
  APPLIED: "Applied",
};

function phaseState(index: number, progress: { index: number; failed: boolean }) {
  if (index > progress.index) return "pending";
  if (index === progress.index) return progress.failed ? "failed" : "current";
  return "done";
}

function timestamp(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not yet";
}

export function WorkflowTimeline({
  status,
  command,
}: {
  status: ScenarioStatus;
  command?: Command | null;
}) {
  const progress = applyProgress(command);

  return (
    <div className="workflow-timeline">
      <ol className="workflow-stages" aria-label="Candidate review progress">
        {WORKFLOW_STAGES.map((stage) => {
          const state = stageState(status, stage);
          return (
            <li key={stage} className={state} aria-current={state === "current" ? "step" : undefined}>
              <b aria-hidden="true" />
              <span>{STAGE_LABELS[stage]}</span>
            </li>
          );
        })}
      </ol>
      {status === "REJECTED" && (
        <p className="workflow-hint">
          Review ended here. A rejected candidate cannot be resubmitted — adjust the layout and
          simulate a new candidate.
        </p>
      )}
      {progress && (
        <ol className="workflow-phases" aria-label="Apply progress">
          {APPLY_PHASES.map((phase, index) => (
            <li key={phase} className={phaseState(index, progress)}>{phase}</li>
          ))}
        </ol>
      )}
      {progress?.failed && (
        <p className="workflow-hint">
          The Fleet Manager bridge did not complete this command, so the factory runtime is
          unchanged. Retry it from Commands.
        </p>
      )}
      {command && (() => {
        const acknowledgedAt = command.attempts
          .map((attempt) => attempt.acknowledged_at)
          .filter((value): value is string => value !== null)
          .at(-1);
        const completedAt = command.attempts
          .map((attempt) => attempt.completed_at)
          .filter((value): value is string => value !== null)
          .at(-1);
        const detail = command.attempts
          .map((attempt) => attempt.detail)
          .filter(Boolean)
          .at(-1);
        return <section className="workflow-command" aria-label="Apply command status">
          <div className="workflow-command-head">
            <strong>Factory apply</strong>
            <span className={`scenario-status ${command.status}`}>{command.status}</span>
          </div>
          <dl>
            <div><dt>Queued</dt><dd>{timestamp(command.created_at)}</dd></div>
            <div><dt>Acknowledged</dt><dd>{timestamp(acknowledgedAt)}</dd></div>
            <div><dt>Finished</dt><dd>{timestamp(completedAt)}</dd></div>
          </dl>
          {detail && <p>{detail}</p>}
          <a href="/commands">Open technical details</a>
        </section>;
      })()}
    </div>
  );
}
