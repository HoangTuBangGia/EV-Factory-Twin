import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { fixtureLayoutVersion } from "@/lib/fixtures";
import { ScenarioRunForm } from "./scenario-run-form";

const layoutSummary = {
  id: fixtureLayoutVersion.layout_id,
  name: fixtureLayoutVersion.name,
  latest_version: fixtureLayoutVersion.version,
  created_by: fixtureLayoutVersion.created_by,
  created_at: fixtureLayoutVersion.created_at,
  archived_at: null,
};

function renderForm(onRun = vi.fn()) {
  render(<ScenarioRunForm
    layouts={[layoutSummary]}
    selectedLayout={fixtureLayoutVersion}
    fieldErrors={{}}
    running={false}
    onSelectLayout={vi.fn()}
    onSelectVersion={vi.fn()}
    onRun={onRun}
  />);
  return onRun;
}

describe("ScenarioRunForm", () => {
  it("keeps advanced assumptions collapsed and uses layout defaults", () => {
    renderForm();

    expect(screen.getByText("Advanced settings").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByLabelText("Robot count")).toHaveValue(5);
    expect(screen.getByLabelText("Task arrival interval (s)")).toHaveValue(8);
    expect(screen.getByLabelText("Robot speed (m/s)")).toHaveValue(1.2);
    expect(screen.getByLabelText("Charger count")).toHaveValue(2);
    expect(screen.getByLabelText("Simulation summary")).toHaveTextContent(
      "5 AMRsBATTERY_DELIVERYDemand every 8sSimulate 3600s",
    );
  });

  it("submits basic settings with the hidden advanced defaults", () => {
    const onRun = renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Run benchmark" }));

    expect(onRun).toHaveBeenCalledWith(expect.objectContaining({
      layout_id: "LAYOUT-DEFAULT",
      route_id: "BATTERY_DELIVERY",
      num_robots: 5,
      task_arrival_interval: 8,
      robot_speed_mps: 1.2,
      charger_count: 2,
      travel_time: 30,
      loading_time: 10,
    }));
  });

  it("submits changed advanced assumptions", () => {
    const onRun = renderForm();
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.change(screen.getByLabelText("Robot speed (m/s)"), { target: { value: "1.8" } });
    fireEvent.change(screen.getByLabelText("Travel time (s)"), { target: { value: "18" } });

    fireEvent.click(screen.getByRole("button", { name: "Run benchmark" }));

    expect(onRun).toHaveBeenCalledWith(expect.objectContaining({
      robot_speed_mps: 1.8,
      travel_time: 18,
    }));
  });

  it("resets edited values and summary to layout defaults", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText("Robot count"), { target: { value: "3" } });
    expect(screen.getByLabelText("Simulation summary")).toHaveTextContent("3 AMRs");

    fireEvent.click(screen.getByRole("button", { name: "Reset to layout defaults" }));

    expect(screen.getByLabelText("Robot count")).toHaveValue(5);
    expect(screen.getByLabelText("Simulation summary")).toHaveTextContent("5 AMRs");
  });
});
