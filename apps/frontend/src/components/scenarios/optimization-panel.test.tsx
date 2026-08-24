import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
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

it("submits a bounded deterministic optimization request", async () => {
  runOptimization.mockResolvedValue({
    evaluated_candidates: 8,
    recommendation: { name: "flow-option-01" },
    ranking: [],
  });
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
});
