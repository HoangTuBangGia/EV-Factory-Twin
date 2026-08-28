"use client";

import { type FormEvent, useState } from "react";
import type { AppRole } from "@/schemas/auth";
import type { ScenarioStatus } from "@/schemas/scenario";

export type ScenarioAction = "run" | "submit" | "approve" | "request-revision" | "apply";

export function ScenarioActions({
  role,
  status,
  activeAction,
  onSubmitScenario,
  onApprove,
  onRequestRevision,
  onStartRevision,
  canStartRevision,
  onApply,
}: {
  role: AppRole;
  status: ScenarioStatus;
  activeAction: ScenarioAction | null;
  onSubmitScenario: () => void;
  onApprove: () => void;
  onRequestRevision: (note: string) => void;
  onStartRevision: () => void;
  canStartRevision: boolean;
  onApply: () => void;
}) {
  const [revisionNote, setRevisionNote] = useState("");

  function requestRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const note = revisionNote.trim();
    if (note) onRequestRevision(note);
  }

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
    if (status === "REVISION_REQUESTED" && canStartRevision) {
      return <div className="button-row scenario-actions">
        <button
          className="button primary"
          type="button"
          disabled={activeAction !== null}
          onClick={onStartRevision}
        >
          Create revised candidate
        </button>
      </div>;
    }
    if (status === "REVISION_REQUESTED") {
      return <div className="review-note">Only the original Designer can create this revision.</div>;
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
      <form className="scenario-revision-form" onSubmit={requestRevision}>
        <label htmlFor="scenario-revision-note">Revision request</label>
        <textarea
          id="scenario-revision-note"
          maxLength={1000}
          rows={3}
          value={revisionNote}
          onChange={(event) => setRevisionNote(event.target.value)}
          placeholder="Explain the exact change needed before approval."
        />
        <div className="button-row scenario-actions">
          <button
            className="button danger"
            type="submit"
            disabled={activeAction !== null || !revisionNote.trim()}
          >
            {activeAction === "request-revision" ? "Requesting…" : "Request changes"}
          </button>
          <button
            className="button"
            type="button"
            disabled={activeAction !== null}
            onClick={onApprove}
          >
            {activeAction === "approve" ? "Approving…" : "Approve"}
          </button>
        </div>
      </form>
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
