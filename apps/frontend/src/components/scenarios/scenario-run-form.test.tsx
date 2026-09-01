import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureLayoutVersion, fixtureScenario } from "@/lib/fixtures";
import { useToastStore } from "@/stores/toast-store";
import {
  formatElapsedTime,
  ScenarioRunForm,
  SIMULATION_SLOW_WARNING_MS,
} from "./scenario-run-form";

const layoutSummary = {
  id: fixtureLayoutVersion.layout_id,
  name: fixtureLayoutVersion.name,
  latest_version: fixtureLayoutVersion.version,
  created_by: fixtureLayoutVersion.created_by,
  created_at: fixtureLayoutVersion.created_at,
  archived_at: null,
};

function renderForm(onRun = vi.fn(), revisionSource = null as typeof fixtureScenario | null) {
  render(<ScenarioRunForm
    layouts={[layoutSummary]}
    selectedLayout={fixtureLayoutVersion}
    revisionSource={revisionSource}
    fieldErrors={{}}
    busy={false}
    running={false}
    onSelectLayout={vi.fn()}
    onSelectVersion={vi.fn()}
    onRun={onRun}
  />);
  return onRun;
}

describe("ScenarioRunForm", () => {
  beforeEach(() => useToastStore.setState({ toasts: [] }));
  afterEach(() => vi.useRealTimers());

  it("formats elapsed time as minutes and zero-padded seconds", () => {
    expect(formatElapsedTime(65)).toBe("1:05");
  });

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

  it("prefills a requested revision and preserves its source in the run payload", () => {
    const onRun = renderForm(vi.fn(), {
      ...fixtureScenario,
      status: "REVISION_REQUESTED",
      review_note: "Move charging away from the aisle.",
    });

    expect(screen.getByLabelText("Scenario name")).toHaveValue("candidate-01-revision");
    expect(screen.getByRole("status")).toHaveTextContent("Move charging away from the aisle.");
    fireEvent.click(screen.getByRole("button", { name: "Run benchmark" }));
    expect(onRun).toHaveBeenCalledWith(expect.objectContaining({
      revision_of: "SCN-0001",
      num_robots: fixtureScenario.config.num_robots,
      route_id: fixtureScenario.config.route_id,
    }));
  });

  it("shows elapsed progress and warns when a simulation takes over a minute", () => {
    vi.useFakeTimers();
    render(<ScenarioRunForm
      layouts={[layoutSummary]}
      selectedLayout={fixtureLayoutVersion}
      fieldErrors={{}}
      busy
      running
      onSelectLayout={vi.fn()}
      onSelectVersion={vi.fn()}
      onRun={vi.fn()}
    />);

    expect(screen.getByRole("timer")).toHaveTextContent("0:00");
    expect(screen.getByRole("progressbar", { name: "Simulation running" }))
      .toHaveAttribute("aria-valuetext", "Elapsed 0 seconds");
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveAttribute(
      "title",
      "Cannot cancel mid-run",
    );

    act(() => vi.advanceTimersByTime(5_000));
    expect(screen.getByRole("timer")).toHaveTextContent("0:05");
    act(() => vi.advanceTimersByTime(SIMULATION_SLOW_WARNING_MS - 5_000));
    expect(screen.getByRole("timer")).toHaveTextContent("1:00");
    expect(useToastStore.getState().toasts).toEqual([
      expect.objectContaining({ type: "info", message: expect.stringContaining("still running") }),
    ]);
  });

  it("cleans up progress and the slow warning when a run finishes", () => {
    vi.useFakeTimers();
    const props = {
      layouts: [layoutSummary],
      selectedLayout: fixtureLayoutVersion,
      fieldErrors: {},
      busy: true,
      running: true,
      onSelectLayout: vi.fn(),
      onSelectVersion: vi.fn(),
      onRun: vi.fn(),
    };
    const { rerender } = render(<ScenarioRunForm {...props}/>);
    act(() => vi.advanceTimersByTime(5_000));

    rerender(<ScenarioRunForm {...props} busy={false} running={false}/>);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run benchmark" })).toBeEnabled();
    act(() => vi.advanceTimersByTime(SIMULATION_SLOW_WARNING_MS));
    expect(useToastStore.getState().toasts).toEqual([]);
  });
});
