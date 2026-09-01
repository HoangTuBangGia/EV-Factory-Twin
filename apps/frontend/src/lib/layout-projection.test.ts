import { describe, expect, it } from "vitest";
import type { LayoutVersion } from "@/schemas/layout";
import type { Scenario } from "@/schemas/scenario";
import { latestAppliedScenario, projectLayoutVersion } from "./layout-projection";

const layout = {
  layout_id: "LAYOUT-A",
  name: "Candidate A",
  version: 2,
  width: 20,
  height: 15,
  stations: [
    { id: "BUFFER", type: "BATTERY_BUFFER", x: 2, y: 4 },
    { id: "MARRIAGE", type: "MARRIAGE_STATION", x: 16, y: 8 },
    { id: "CHARGER", type: "CHARGING_STATION", x: 2, y: 12 },
  ],
  routes: [{
    id: "DELIVERY",
    kind: "DELIVERY",
    start_station_id: "BUFFER",
    end_station_id: "MARRIAGE",
    waypoints: [{ x: 2, y: 4 }, { x: 16, y: 8 }],
  }],
  no_go_zones: [],
  congestion_zones: [],
  config: {
    robot_count: 2,
    demand_interval_seconds: 5,
    robot_speed_mps: 1,
    charger_count: 1,
  },
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-08-24T00:00:00Z",
  archived_at: null,
} satisfies LayoutVersion;

it("projects the immutable API layout into the shared map contract", () => {
  expect(projectLayoutVersion(layout, "DELIVERY")).toMatchObject({
    id: "LAYOUT-A",
    version: 2,
    active_route_id: "DELIVERY",
    routes: [{ id: "DELIVERY", kind: "DELIVERY", waypoints: layout.routes[0].waypoints }],
    congestion_zones: layout.congestion_zones,
    config: layout.config,
  });
});

describe("latestAppliedScenario", () => {
  it("selects the most recently applied scenario", () => {
    const scenario = (id: string, appliedAt: string): Scenario => ({
      id,
      name: id,
      status: "APPLIED",
      config: {
        num_robots: 2, num_tasks: 10, task_arrival_interval: 5, travel_time: 20,
        loading_time: 5, simulation_time: 100, layout_id: "LAYOUT-A",
        layout_version: 2, route_id: "DELIVERY", robot_speed_mps: 1,
        charger_count: 1, route_distance_m: 20, congestion_multiplier: 1,
      },
      metrics: {
        completed_tasks: 10, unfinished_tasks: 0, completion_rate: 1,
        throughput_per_hour: 360, average_cycle_time: 20, average_waiting_time: 0,
        fleet_utilization_percent: 50, starvation_events: 0, congestion_percent: 0,
        travel_distance: 200, average_delivery_delay: 0,
      },
      duration_ms: 1,
      created_at: appliedAt,
      created_by: null,
      reviewed_at: appliedAt,
      reviewed_by: null,
      applied_at: appliedAt,
      applied_by: null,
      version: 1,
    });

    expect(latestAppliedScenario([
      scenario("SCN-OLD", "2026-08-23T00:00:00Z"),
      scenario("SCN-NEW", "2026-08-24T00:00:00Z"),
    ])?.id).toBe("SCN-NEW");
  });
});
