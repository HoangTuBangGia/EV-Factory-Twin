import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScenarioActions } from "./scenario-actions";

function renderActions(
  role: "DESIGNER" | "MONITOR",
  status: "SIMULATED" | "SUBMITTED" | "APPROVED",
) {
  const onSubmitScenario = vi.fn();
  const onReview = vi.fn();
  const onApply = vi.fn();
  render(
    <ScenarioActions
      role={role}
      status={status}
      activeAction={null}
      onSubmitScenario={onSubmitScenario}
      onReview={onReview}
      onApply={onApply}
    />,
  );
  return { onSubmitScenario, onReview, onApply };
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

  it("lets a Monitor approve or reject a submitted scenario", () => {
    const { onReview } = renderActions("MONITOR", "SUBMITTED");
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(onReview).toHaveBeenNthCalledWith(1, "approve");
    expect(onReview).toHaveBeenNthCalledWith(2, "reject");
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
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
