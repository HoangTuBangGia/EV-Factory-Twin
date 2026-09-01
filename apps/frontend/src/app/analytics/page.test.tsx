import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import { fixtureMetrics } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import AnalyticsPage from "./page";

vi.mock("@/lib/env", () => ({ usesMockData: false }));
vi.mock("@/lib/api-client", () => ({ apiClient: { getMetricHistory: vi.fn() } }));
vi.mock("@/components/dashboard/kpi-grid", () => ({ KpiGrid: () => <div>KPI grid</div> }));
vi.mock("@/components/charts/operations-chart", () => ({
  OperationsChart: ({ mode }: { mode: string }) => <div>{mode} chart</div>,
  OPERATIONS_TREND_LIVE_LABEL: "persisted and live",
}));

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useFactoryStore.getState().reset();
  });

  it("hydrates recent KPI history without replacing live samples", async () => {
    const now = Date.now();
    useFactoryStore.getState().hydrateMetricsHistory([{
      ...fixtureMetrics,
      throughput_per_hour: 99,
      timestamp: now,
    }]);
    vi.mocked(apiClient.getMetricHistory).mockResolvedValue({
      items: [{
        recorded_at: new Date(now - 5_000).toISOString(),
        simulated_elapsed_seconds: 5,
        metrics: fixtureMetrics,
        scenario_id: null,
      }],
      next_offset: null,
    });

    render(<AnalyticsPage/>);

    await waitFor(() => expect(apiClient.getMetricHistory).toHaveBeenCalledOnce());
    expect(useFactoryStore.getState().metricsHistory).toHaveLength(2);
    expect(useFactoryStore.getState().metricsHistory.at(-1)?.throughput_per_hour).toBe(99);
  });

  it("keeps live analytics usable when history is unavailable", async () => {
    useFactoryStore.getState().setMetrics(fixtureMetrics);
    vi.mocked(apiClient.getMetricHistory).mockRejectedValue(new Error("offline"));

    render(<AnalyticsPage/>);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Historical KPI data is unavailable; live metrics will continue updating.",
    );
    expect(useFactoryStore.getState().metrics).toEqual(fixtureMetrics);
    expect(screen.getByText("throughput chart")).toBeInTheDocument();
  });
});
