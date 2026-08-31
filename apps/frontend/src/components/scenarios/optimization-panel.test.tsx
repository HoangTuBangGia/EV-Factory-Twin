import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LayoutVersion } from "@/schemas/layout";
import { OptimizationPanel } from "./optimization-panel";

const runOptimization = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiClient: { runOptimization } }));

const layout = {
  layout_id: "LAYOUT-DEFAULT",
  name: "Default",
  version: 1,
  width: 20,
  height: 15,
  stations: [],
  routes: [{
    id: "BATTERY_DELIVERY",
    kind: "DELIVERY",
    start_station_id: "BATTERY_BUFFER",
    end_station_id: "MARRIAGE_STATION",
    waypoints: [{ x: 2, y: 4 }, { x: 16, y: 8 }],
  }],
  no_go_zones: [],
  congestion_zones: [],
  config: { robot_count: 2, demand_interval_seconds: 5, robot_speed_mps: 1, charger_count: 1 },
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-08-24T00:00:00Z",
  archived_at: null,
} satisfies LayoutVersion;

function renderPanel() {
  render(<OptimizationPanel
    layouts={[{
      id: layout.layout_id,
      name: layout.name,
      latest_version: layout.version,
      created_by: layout.created_by,
      created_at: layout.created_at,
      archived_at: null,
    }]}
    selectedLayout={layout}
  />);
}

describe("OptimizationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runOptimization.mockResolvedValue({
      evaluated_candidates: 8,
      recommendation: { id: "SCN-OPT-01", name: "flow-option-01" },
      ranking: [],
    });
  });

  it("stays collapsed until a Designer opens the advanced workflow", () => {
    renderPanel();

    expect(screen.getByText("Advanced · Optimize multiple options").closest("details"))
      .not.toHaveAttribute("open");
    expect(screen.getByText("8 combinations · maximum 64")).toBeInTheDocument();
  });

  it("submits a bounded deterministic optimization request", async () => {
    renderPanel();
    fireEvent.click(screen.getByText("Advanced · Optimize multiple options"));

    fireEvent.click(screen.getByRole("button", { name: "Evaluate candidates" }));

    await waitFor(() => expect(runOptimization).toHaveBeenCalledOnce());
    expect(runOptimization.mock.calls[0]?.[0]).toMatchObject({
      layouts: [{ layout_id: "LAYOUT-DEFAULT", layout_version: 1 }],
      route_ids: ["BATTERY_DELIVERY"],
      robot_counts: [2, 3],
      robot_speeds_mps: [0.8, 1],
      charger_counts: [1, 2],
    });
    expect(await screen.findByText(/from 8 candidates/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open recommended candidate" }))
      .toHaveAttribute("href", "/scenarios?candidate=SCN-OPT-01");
  });

  it("blocks a Cartesian product above the backend limit", () => {
    renderPanel();
    fireEvent.click(screen.getByText("Advanced · Optimize multiple options"));
    fireEvent.change(screen.getByLabelText("Robot counts"), {
      target: { value: "1,2,3,4,5,6,7,8" },
    });
    fireEvent.change(screen.getByLabelText("Demand intervals (s)"), {
      target: { value: "4,5,6" },
    });

    expect(screen.getByRole("status")).toHaveTextContent("96 candidates");
    expect(screen.getByText(/Reduce the dimensions/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Evaluate candidates" })).toBeDisabled();
  });
});
