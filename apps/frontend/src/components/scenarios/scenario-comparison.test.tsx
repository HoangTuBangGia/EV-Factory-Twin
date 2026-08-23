import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScenarioMetrics } from "@/schemas/scenario";
import { ScenarioComparison, ScenarioStatusBadge } from "./scenario-comparison";

const baseline: ScenarioMetrics = {
  completed_tasks: 200,
  unfinished_tasks: 100,
  completion_rate: 0.67,
  throughput_per_hour: 200,
  average_cycle_time: 120,
  average_waiting_time: 70,
  fleet_utilization_percent: 75,
  starvation_events: 2,
  congestion_percent: 10,
  travel_distance: 1_200,
  average_delivery_delay: 5,
};

describe("ScenarioComparison", () => {
  it("marks higher throughput and lower waiting time as improvements", () => {
    render(<ScenarioComparison baseline={baseline} candidate={{
      ...baseline,
      throughput_per_hour: 240,
      average_waiting_time: 50,
      average_delivery_delay: 8,
    }} />);

    expect(screen.getAllByText("Better")).toHaveLength(2);
    expect(screen.getByText("Worse")).toBeInTheDocument();
    expect(screen.getAllByText("Same")).toHaveLength(6);
  });

  it("renders the workflow status", () => {
    render(<ScenarioStatusBadge status="APPROVED" />);
    expect(screen.getByText("APPROVED")).toHaveClass("APPROVED");
  });
});
