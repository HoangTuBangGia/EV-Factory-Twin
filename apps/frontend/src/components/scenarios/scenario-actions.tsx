import type { AppRole } from "@/schemas/auth";
import type { ScenarioStatus } from "@/schemas/scenario";

export type ScenarioAction = "run" | "submit" | "approve" | "reject" | "apply";

export function ScenarioActions({
  role,
  status,
  activeAction,
  onSubmitScenario,
  onReview,
  onApply,
}: {
  role: AppRole;
  status: ScenarioStatus;
  activeAction: ScenarioAction | null;
  onSubmitScenario: () => void;
  onReview: (action: "approve" | "reject") => void;
  onApply: () => void;
}) {
  if (role === "DESIGNER") {
    if (status === "SIMULATED") {
      return <div className="button-row scenario-actions">
        <button
          className="button primary"
          type="button"
          disabled={activeAction !== null}
          onClick={onSubmitScenario}
        >
          {activeAction === "submit" ? "Submitting…" : "Submit for review"}
        </button>
      </div>;
    }
    return (
      <div className="review-note">
        {status === "SUBMITTED"
          ? "Waiting for Monitor review. Designers cannot approve or apply their own scenario."
          : `This scenario is ${status.toLowerCase()}. Review and apply actions belong to a Monitor.`}
      </div>
    );
  }

  if (status === "SUBMITTED") {
    return (
      <div className="button-row scenario-actions">
        <button
          className="button danger"
          type="button"
          disabled={activeAction !== null}
          onClick={() => onReview("reject")}
        >
          {activeAction === "reject" ? "Rejecting…" : "Reject"}
        </button>
        <button
          className="button"
          type="button"
          disabled={activeAction !== null}
          onClick={() => onReview("approve")}
        >
          {activeAction === "approve" ? "Approving…" : "Approve"}
        </button>
      </div>
    );
  }

  if (status === "SIMULATED") {
    return <div className="review-note">Waiting for the Designer to submit this scenario.</div>;
  }

  if (status === "APPROVED") {
    return (
      <div className="button-row scenario-actions">
        <button
          className="button primary"
          type="button"
          disabled={activeAction !== null}
          onClick={onApply}
        >
          {activeAction === "apply" ? "Applying…" : "Apply to factory"}
        </button>
      </div>
    );
  }

  return <div className="review-note">No review action is available for a {status.toLowerCase()} scenario.</div>;
}
