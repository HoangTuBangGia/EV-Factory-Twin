import { describe, expect, it } from "vitest";
import { commandSchema } from "./command";
import { layoutVersionSchema } from "./layout";
import { optimizationRequestSchema } from "./optimization";
import { factoryEventSchema } from "./websocket-event";

const config = {
  num_robots: 2, num_tasks: 20, task_arrival_interval: 5, travel_time: 30,
  loading_time: 5, simulation_time: 600, layout_id: "LAYOUT-DEFAULT",
  layout_version: 1, route_id: "BATTERY_DELIVERY", robot_speed_mps: 1,
  charger_count: 1, route_distance_m: 30, congestion_multiplier: 1,
};

const command = {
  operation_id: "33333333-3333-4333-8333-333333333333",
  scenario_id: "SCN-0001", status: "PENDING", payload: config,
  timeout_seconds: 30, max_retries: 1,
  attempts: [{ attempt_number: 1, status: "PENDING", leased_by: null,
    lease_expires_at: null, acknowledged_at: null, completed_at: null, detail: "" }],
  requested_by: "22222222-2222-4222-8222-222222222222",
  created_at: "2026-08-24T00:00:00.000Z", updated_at: "2026-08-24T00:00:00.000Z",
};

describe("advanced MVP backend contracts", () => {
  it("parses an immutable layout version with congestion and runtime config", () => {
    const layout = layoutVersionSchema.parse({
      layout_id: "LAYOUT-DEFAULT", name: "Battery transfer zone", version: 1,
      width: 20, height: 15,
      stations: [
        { id: "BATTERY_BUFFER", type: "BATTERY_BUFFER", x: 2, y: 4 },
        { id: "MARRIAGE_STATION", type: "MARRIAGE_STATION", x: 16, y: 8 },
        { id: "CHARGING_STATION", type: "CHARGING_STATION", x: 2, y: 12 },
      ],
      routes: [{ id: "BATTERY_DELIVERY", start_station_id: "BATTERY_BUFFER",
        end_station_id: "MARRIAGE_STATION", waypoints: [{ x: 2, y: 4 }, { x: 16, y: 8 }] }],
      no_go_zones: [],
      congestion_zones: [{ id: "CONGESTION_01", delay_multiplier: 1.25,
        points: [{ x: 10, y: 6 }, { x: 13, y: 6 }, { x: 13, y: 9 }] }],
      config: { robot_count: 2, demand_interval_seconds: 8, robot_speed_mps: 1, charger_count: 1 },
      created_by: "11111111-1111-4111-8111-111111111111",
      created_at: "2026-08-24T00:00:00.000Z", archived_at: null,
    });
    expect(layout.congestion_zones[0].delay_multiplier).toBe(1.25);
    expect(layout.routes[0].kind).toBe("DELIVERY");
  });

  it("parses command.updated without dropping command lifecycle data", () => {
    expect(commandSchema.parse(command).operation_id).toBe(command.operation_id);
    expect(factoryEventSchema.parse({ type: "command.updated", data: command })).toEqual({
      type: "command.updated", data: command,
    });
  });

  it("rejects an optimization search larger than 64 candidates", () => {
    const result = optimizationRequestSchema.safeParse({
      name_prefix: "candidate",
      layouts: [{ layout_id: "LAYOUT-DEFAULT", layout_version: 1 },
        { layout_id: "LAYOUT-DEFAULT", layout_version: 2 }],
      route_ids: ["ROUTE_1", "ROUTE_2"], robot_counts: [2, 3, 4],
      robot_speeds_mps: [1, 1.5, 2], charger_counts: [1, 2], demand_intervals: [5],
    });
    expect(result.success).toBe(false);
  });
});
