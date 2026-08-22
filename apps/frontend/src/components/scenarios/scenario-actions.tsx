import type { AppRole } from "@/schemas/auth";
import type { ScenarioStatus } from "@/schemas/scenario";

export type ScenarioAction = "run" | "approve" | "reject" | "apply";

export function ScenarioActions({
  role,
  status,
  activeAction,
  onReview,
  onApply,
}: {
  role: AppRole;
  status: ScenarioStatus;
  activeAction: ScenarioAction | null;
  onReview: (action: "approve" | "reject") => void;
  onApply: () => void;
}) {
  if (role === "DESIGNER") {
    return (
      <div className="review-note">
        {status === "SIMULATED"
          ? "Waiting for monitor review. Designers cannot approve or apply their own scenario."
          : `This scenario is ${status.toLowerCase()}. Review and apply actions belong to a Monitor.`}
      </div>
    );
  }

  if (status === "SIMULATED") {
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
