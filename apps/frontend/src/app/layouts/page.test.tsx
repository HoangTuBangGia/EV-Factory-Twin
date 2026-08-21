import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LayoutsPage from "./page";

const authState = vi.hoisted(() => ({ role: "DESIGNER" as "DESIGNER" | "MONITOR" }));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: authState.role } }),
}));

describe("LayoutsPage", () => {
  beforeEach(() => { authState.role = "DESIGNER"; });

  it("updates station coordinates in the live preview and resets the draft", () => {
    const { container } = render(<LayoutsPage/>);
    const xInput = screen.getByLabelText("X (m)", { selector: "#BATTERY_BUFFER-x" });

    fireEvent.change(xInput, { target: { value: "4.2" } });
    expect(xInput).toHaveValue(4);
    expect(container.querySelector('.fm-zone circle[cx="4"]')).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reset draft" }));
    expect(container.querySelector('.fm-zone circle[cx="2"]')).toBeInTheDocument();
  });

  it("supports adding and removing route waypoints", () => {
    render(<LayoutsPage/>);
    expect(screen.getAllByLabelText(/BATTERY_DELIVERY waypoint \d+ X/)).toHaveLength(4);

    fireEvent.click(screen.getByRole("button", { name: "Add waypoint" }));
    expect(screen.getAllByLabelText(/BATTERY_DELIVERY waypoint \d+ X/)).toHaveLength(5);

    fireEvent.click(screen.getByRole("button", { name: "Remove BATTERY_DELIVERY waypoint 5" }));
    expect(screen.getAllByLabelText(/BATTERY_DELIVERY waypoint \d+ X/)).toHaveLength(4);
  });

  it("blocks non-Designer roles", () => {
    authState.role = "MONITOR";
    render(<LayoutsPage/>);
    expect(screen.getByText("Designer access required")).toBeInTheDocument();
    expect(screen.queryByText("Candidate geometry")).not.toBeInTheDocument();
  });
});
