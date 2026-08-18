import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScenarioActions } from "./scenario-actions";

function renderActions(role: "DESIGNER" | "MONITOR" | "ADMIN", status: "SIMULATED" | "APPROVED") {
  const onReview = vi.fn();
  const onApply = vi.fn();
  render(
    <ScenarioActions
      role={role}
      status={status}
      activeAction={null}
      onReview={onReview}
      onApply={onApply}
    />,
  );
  return { onReview, onApply };
}

describe("ScenarioActions", () => {
  it("shows a waiting message without review controls for a Designer", () => {
    renderActions("DESIGNER", "SIMULATED");
    expect(screen.getByText(/Waiting for monitor review/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
  });

  it("lets a Monitor approve or reject a simulated scenario", () => {
    const { onReview } = renderActions("MONITOR", "SIMULATED");
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(onReview).toHaveBeenNthCalledWith(1, "approve");
    expect(onReview).toHaveBeenNthCalledWith(2, "reject");
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
  });

  it("only shows Apply to a Monitor after approval", () => {
    const { onApply } = renderActions("MONITOR", "APPROVED");
    fireEvent.click(screen.getByRole("button", { name: "Apply to factory" }));
    expect(onApply).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("keeps Administrator access read-only", () => {
    renderActions("ADMIN", "APPROVED");
    expect(screen.getByText(/read-only/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
