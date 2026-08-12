import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "./api-client";

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
