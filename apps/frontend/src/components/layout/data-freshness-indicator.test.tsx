import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useFactoryStore } from "@/stores/factory-store";
import {
  DATA_STALE_AFTER_MS,
  DataFreshnessIndicator,
  formatDataFreshness,
  isDataStale,
} from "./data-freshness-indicator";

describe("data freshness", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-30T12:00:00.000Z"));
    useFactoryStore.getState().reset();
  });

  afterEach(() => vi.useRealTimers());

  it("formats seconds, minutes, old timestamps, and missing data", () => {
    const now = Date.now();
    expect(formatDataFreshness(null, now)).toBe("Waiting for data");
    expect(formatDataFreshness(now - 3_000, now)).toBe("Updated 3s ago");
    expect(formatDataFreshness(now - 120_000, now)).toBe("Updated 2m ago");
    expect(formatDataFreshness(now - 3_600_000, now)).toContain("2026");
  });

  it("only treats data older than 30 seconds as stale while live", () => {
    const now = Date.now();
    expect(isDataStale("LIVE", now - DATA_STALE_AFTER_MS, now)).toBe(false);
    expect(isDataStale("LIVE", now - DATA_STALE_AFTER_MS - 1, now)).toBe(true);
    expect(isDataStale("MOCK", now - DATA_STALE_AFTER_MS - 1, now)).toBe(false);
    expect(isDataStale("LIVE", null, now)).toBe(false);
  });

  it("updates relative time and warns when live data becomes stale", () => {
    useFactoryStore.setState({ connectionStatus: "LIVE", lastUpdateAt: Date.now() });
    render(<DataFreshnessIndicator/>);
    expect(screen.getByText("Updated 0s ago")).toBeInTheDocument();
    expect(screen.queryByText("Data may be stale")).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(DATA_STALE_AFTER_MS + 1_000));
    expect(screen.getByText("Updated 31s ago")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Data may be stale");
  });
});
