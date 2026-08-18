import { describe, expect, it } from "vitest";
import { scenarioSchema } from "./scenario";

const scenarioResponse = {
  id: "SCN-0001",
  name: "candidate-01",
  status: "APPROVED",
  config: {
    num_robots: 5,
    num_tasks: 500,
    task_arrival_interval: 5,
    travel_time: 30,
    loading_time: 10,
    simulation_time: 3600,
  },
  metrics: {
    completed_tasks: 355,
    unfinished_tasks: 145,
    completion_rate: 0.71,
    throughput_per_hour: 355,
    average_cycle_time: 900,
    average_waiting_time: 850,
  },
  duration_ms: 2.4,
  created_at: "2026-08-14T00:00:00.000Z",
  created_by: "11111111-1111-4111-8111-111111111111",
  reviewed_at: "2026-08-14T00:05:00.000Z",
  reviewed_by: "22222222-2222-4222-8222-222222222222",
  applied_at: null,
  applied_by: null,
  version: 2,
};

describe("scenarioSchema backend contract", () => {
  it("preserves workflow actors, timestamps, and optimistic-lock version", () => {
    const parsed = scenarioSchema.parse(scenarioResponse);

    expect(parsed).toMatchObject({
      created_at: scenarioResponse.created_at,
      created_by: scenarioResponse.created_by,
      reviewed_at: scenarioResponse.reviewed_at,
      reviewed_by: scenarioResponse.reviewed_by,
      applied_at: null,
      applied_by: null,
      version: 2,
    });
  });

  it("rejects a response that omits required provenance fields", () => {
    const withoutVersion: Record<string, unknown> = { ...scenarioResponse };
    delete withoutVersion.version;
    expect(scenarioSchema.safeParse(withoutVersion).success).toBe(false);
  });

  it("rejects a non-UTC serialized timestamp", () => {
    expect(scenarioSchema.safeParse({
      ...scenarioResponse,
      created_at: "2026-08-14T07:00:00.000+07:00",
    }).success).toBe(false);
  });
});
