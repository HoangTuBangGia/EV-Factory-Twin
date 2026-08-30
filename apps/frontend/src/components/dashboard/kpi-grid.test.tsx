import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { fixtureMetrics, fixtureRobots } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { KpiGrid } from "./kpi-grid";

describe("KpiGrid", () => {
  beforeEach(() => { useFactoryStore.getState().setMetrics(fixtureMetrics); useFactoryStore.getState().setRobots(fixtureRobots); });
  it("formats throughput", () => { render(<KpiGrid/>); expect(screen.getByText("61.4 tasks/h")).toBeInTheDocument(); });

  it("describes every live KPI without inventing a congestion metric", () => {
    render(<KpiGrid/>);

    expect(screen.getAllByRole("tooltip")).toHaveLength(5);
    expect(screen.getByRole("article", { name: "Throughput" }))
      .toHaveAccessibleDescription("Số task hoàn thành/giờ. Cao hơn = tốt hơn.");
    expect(screen.getByRole("article", { name: "Starvation" }))
      .toHaveAccessibleDescription(/0 = lý tưởng; >5 = cần thêm fleet/);
    expect(screen.getByRole("article", { name: "Active tasks" }))
      .toHaveAccessibleDescription(/Số task đang được xử lý/);
    expect(screen.queryByText("Congestion")).not.toBeInTheDocument();
  });
});
