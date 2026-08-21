import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  apiClient,
  setApiAccessToken,
  setApiUnauthorizedHandler,
} from "./api-client";

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
  created_at: "2026-08-14T00:00:00.000Z",
  created_by: "11111111-1111-4111-8111-111111111111",
  reviewed_at: null,
  reviewed_by: null,
  applied_at: null,
  applied_by: null,
  version: 1,
};

describe("apiClient mock configuration", () => {
  afterEach(() => {
    setApiAccessToken(null);
    setApiUnauthorizedHandler(null);
    vi.restoreAllMocks();
  });

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
  afterEach(() => {
    setApiAccessToken(null);
    setApiUnauthorizedHandler(null);
    vi.restoreAllMocks();
  });

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

  it("recovers the scenario list after a refresh", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([scenario]), { status: 200 }),
    );

    await expect(apiClient.getScenarios()).resolves.toEqual([scenario]);
  });
});

describe("apiClient authentication", () => {
  afterEach(() => {
    setApiAccessToken(null);
    setApiUnauthorizedHandler(null);
    vi.restoreAllMocks();
  });

  it("attaches the current access token and validates /auth/me", async () => {
    const currentUser = {
      id: "11111111-1111-4111-8111-111111111111",
      email: "designer@example.com",
      display_name: "Demo Designer",
      role: "DESIGNER",
      is_active: true,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(currentUser), { status: 200 }),
    );
    setApiAccessToken("access-token-for-test");

    await expect(apiClient.getCurrentUser()).resolves.toEqual(currentUser);
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer access-token-for-test");
  });

  it("preserves HTTP status for permission handling", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Insufficient role" }), { status: 403 }),
    );

    const error = await apiClient.approveScenario(scenario.id).catch((cause: unknown) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 403, detail: "Insufficient role" });
  });

  it("notifies the auth boundary when an access token is rejected", async () => {
    const onUnauthorized = vi.fn();
    setApiUnauthorizedHandler(onUnauthorized);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid or expired access token" }), { status: 401 }),
    );

    await expect(apiClient.getRobots()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });
});
