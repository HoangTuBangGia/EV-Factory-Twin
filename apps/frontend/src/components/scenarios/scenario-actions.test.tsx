import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScenarioActions } from "./scenario-actions";

function renderActions(
  role: "DESIGNER" | "MONITOR",
  status: "SIMULATED" | "SUBMITTED" | "APPROVED" | "REVISION_REQUESTED",
) {
  const onSubmitScenario = vi.fn();
  const onApprove = vi.fn();
  const onRequestRevision = vi.fn();
  const onStartRevision = vi.fn();
  const onApply = vi.fn();
  render(
    <ScenarioActions
      role={role}
      status={status}
      activeAction={null}
      onSubmitScenario={onSubmitScenario}
      onApprove={onApprove}
      onRequestRevision={onRequestRevision}
      onStartRevision={onStartRevision}
      canStartRevision
      onApply={onApply}
    />,
  );
  return { onSubmitScenario, onApprove, onRequestRevision, onStartRevision, onApply };
}

describe("ScenarioActions", () => {
  it("lets a Designer submit a simulated scenario", () => {
    const { onSubmitScenario } = renderActions("DESIGNER", "SIMULATED");
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    expect(onSubmitScenario).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
  });

  it("shows a waiting message after a Designer submits", () => {
    renderActions("DESIGNER", "SUBMITTED");
    expect(screen.getByText(/Waiting for Monitor review/i)).toBeInTheDocument();
  });

  it("lets a Monitor approve or request a revision with a note", () => {
    const { onApprove, onRequestRevision } = renderActions("MONITOR", "SUBMITTED");
    const requestButton = screen.getByRole("button", { name: "Request changes" });
    expect(requestButton).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Revision request"), {
      target: { value: "  Move charging away from the aisle.  " },
    });
    fireEvent.click(requestButton);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onRequestRevision).toHaveBeenCalledWith("Move charging away from the aisle.");
    expect(onApprove).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
  });

  it("lets the original Designer start a requested revision", () => {
    const { onStartRevision } = renderActions("DESIGNER", "REVISION_REQUESTED");
    fireEvent.click(screen.getByRole("button", { name: "Create revised candidate" }));
    expect(onStartRevision).toHaveBeenCalledOnce();
  });

  it("does not let a Monitor review an unsubmitted scenario", () => {
    renderActions("MONITOR", "SIMULATED");
    expect(screen.getByText(/Waiting for the Designer/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("only shows Apply to a Monitor after approval", () => {
    const { onApply } = renderActions("MONITOR", "APPROVED");
    fireEvent.click(screen.getByRole("button", { name: "Apply to factory" }));
    expect(onApply).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

});
