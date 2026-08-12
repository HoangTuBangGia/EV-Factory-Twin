import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { fixtureMetrics, fixtureRobots } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { KpiGrid } from "./kpi-grid";

describe("KpiGrid", () => {
  beforeEach(() => { useFactoryStore.getState().setMetrics(fixtureMetrics); useFactoryStore.getState().setRobots(fixtureRobots); });
  it("formats throughput", () => { render(<KpiGrid/>); expect(screen.getByText("61.4 tasks/h")).toBeInTheDocument(); });
});
