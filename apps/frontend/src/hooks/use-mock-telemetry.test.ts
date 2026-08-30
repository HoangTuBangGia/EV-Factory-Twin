import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureRobots } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { useMockTelemetry } from "./use-mock-telemetry";

vi.mock("@/lib/env", () => ({ usesMockData: true }));

describe("useMockTelemetry", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-30T12:00:00.000Z"));
    useFactoryStore.getState().reset();
    useFactoryStore.getState().setRobots(fixtureRobots);
  });

  afterEach(() => vi.useRealTimers());

  it("freezes fixture robots while paused and resumes from the frozen pose", () => {
    renderHook(() => useMockTelemetry());
    const initialX = useFactoryStore.getState().robots["AMR-01"].pose.x;

    act(() => useFactoryStore.getState().setPaused(true));
    act(() => vi.advanceTimersByTime(400));
    expect(useFactoryStore.getState().robots["AMR-01"].pose.x).toBe(initialX);
    expect(useFactoryStore.getState().lastUpdateAt).toBeNull();

    act(() => useFactoryStore.getState().setPaused(false));
    act(() => vi.advanceTimersByTime(200));
    expect(useFactoryStore.getState().robots["AMR-01"].pose.x).not.toBe(initialX);
    expect(useFactoryStore.getState().lastUpdateAt).toBe(Date.now());
  });
});
