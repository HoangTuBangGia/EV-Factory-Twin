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
    </div>
  );
}
