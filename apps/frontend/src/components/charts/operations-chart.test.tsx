import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureMetrics } from "@/lib/fixtures";
import { METRICS_HISTORY_SAMPLE_INTERVAL_MS, useFactoryStore } from "@/stores/factory-store";
import { OperationsChart } from "./operations-chart";

vi.mock("@/lib/env", () => ({ usesMockData: false }));

vi.mock("echarts-for-react", () => ({
  default: ({ option, lazyUpdate }: {
    option: {
      xAxis: { type: string };
      series: Array<{ data: unknown[]; showSymbol: boolean }>;
    };
    lazyUpdate: boolean;
  }) => (
    <div
      data-axis-type={option.xAxis.type}
      data-lazy-update={String(lazyUpdate)}
      data-points={String(option.series[0]?.data.length ?? 0)}
      data-show-symbol={String(option.series[0]?.showSymbol)}
      data-testid="echarts"
    />
  ),
}));

describe("OperationsChart", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-13T08:00:00Z"));
    useFactoryStore.getState().clearMetricsHistory();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("shows an empty state until live metrics arrive", () => {
    render(<OperationsChart />);

    expect(screen.getByText(/waiting for the first metrics update/i)).toBeInTheDocument();
  });

  it("renders sampled metrics on a lazy time-series chart without point symbols", () => {
    useFactoryStore.getState().setMetrics(fixtureMetrics);
    vi.advanceTimersByTime(METRICS_HISTORY_SAMPLE_INTERVAL_MS);
    useFactoryStore.getState().setMetrics({
      ...fixtureMetrics,
      throughput_per_hour: fixtureMetrics.throughput_per_hour + 1,
    });

    render(<OperationsChart />);

    const chart = screen.getByTestId("echarts");
    expect(chart).toHaveAttribute("data-axis-type", "time");
    expect(chart).toHaveAttribute("data-lazy-update", "true");
    expect(chart).toHaveAttribute("data-points", "2");
    expect(chart).toHaveAttribute("data-show-symbol", "false");
  });
});
