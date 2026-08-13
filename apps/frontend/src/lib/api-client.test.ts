import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "./api-client";

const scenario = {
  id: "SCN-0001",
  name: "candidate-01",
  status: "SIMULATED",
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
  reviewed_at: null,
  applied_at: null,
};

describe("apiClient mock configuration", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the backend /api/v1/mock/config contract", async () => {
    const config = {
      robot_count: 5,
      task_interval_seconds: 8,
      robot_speed_mps: 1.2,
      simulation_speed: 1,
      low_battery_threshold: 20,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(config), { status: 200 }),
    );

    await apiClient.updateMockConfig(config);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/mock/config",
      expect.objectContaining({ method: "POST", body: JSON.stringify(config) }),
    );
  });
});

describe("apiClient scenario workflow", () => {
  afterEach(() => vi.restoreAllMocks());

  it("runs a scenario with the agreed request body", async () => {
    const input = { name: scenario.name, ...scenario.config };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(scenario), { status: 200 }),
    );

    await apiClient.runScenario(input);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/scenarios/run",
      expect.objectContaining({ method: "POST" }),
    );
    const requestBody = fetchMock.mock.calls[0]?.[1]?.body;
    expect(JSON.parse(String(requestBody))).toEqual(input);
  });

  it.each([
    ["approve", "approveScenario"],
    ["reject", "rejectScenario"],
    ["apply", "applyScenario"],
  ] as const)("uses the %s workflow endpoint", async (action, method) => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(scenario), { status: 200 }),
    );

    await apiClient[method](scenario.id);

    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/scenarios/${scenario.id}/${action}`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("surfaces a backend conflict detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Scenario must be APPROVED" }), { status: 409 }),
    );

    await expect(apiClient.applyScenario(scenario.id)).rejects.toThrow("Scenario must be APPROVED");
  });
});
