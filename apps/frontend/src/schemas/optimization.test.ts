import { describe, expect, it } from "vitest";
import {
  optimizationCandidateCount,
  optimizationRequestSchema,
} from "./optimization";

const dimensions = {
  layouts: [{ layout_id: "LAYOUT-DEFAULT", layout_version: 1 }],
  route_ids: ["BATTERY_DELIVERY"],
  robot_counts: [2, 3],
  robot_speeds_mps: [0.8, 1],
  charger_counts: [1, 2],
  demand_intervals: [5],
};

describe("optimization candidate limit", () => {
  it("counts the Cartesian product shared by the UI and schema", () => {
    expect(optimizationCandidateCount(dimensions)).toBe(8);
  });

  it("rejects more than 64 combinations", () => {
    const parsed = optimizationRequestSchema.safeParse({
      ...dimensions,
      name_prefix: "flow-option",
      robot_counts: [1, 2, 3, 4, 5, 6, 7, 8],
      demand_intervals: [4, 5, 6],
      num_tasks: 100,
      loading_time: 5,
      simulation_time: 3600,
    });

    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toContain("64 candidates");
  });
});
