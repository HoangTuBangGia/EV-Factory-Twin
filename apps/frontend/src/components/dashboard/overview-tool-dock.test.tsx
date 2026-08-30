import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OverviewToolDock } from "./overview-tool-dock";

vi.mock("@/stores/factory-store", () => ({
  useFactoryStore: (select: (state: unknown) => unknown) => select({
    robots: { "AMR-01": {}, "AMR-02": {} },
    alerts: [{ id: "ALERT-01" }],
    paused: false,
    togglePaused: vi.fn(),
  }),
}));
vi.mock("@/components/dashboard/kpi-grid", () => ({ KpiGrid: () => <div>kpi content</div> }));
vi.mock("@/components/charts/operations-chart", () => ({
  OperationsChart: () => <div>chart content</div>,
  OPERATIONS_TREND_LIVE_LABEL: "live trend",
}));
vi.mock("@/components/fleet/fleet-table", () => ({ FleetTable: () => <div>fleet content</div> }));
vi.mock("@/components/alerts/alert-list", () => ({ AlertList: () => <div>alert content</div> }));

describe("OverviewToolDock", () => {
  it("orders the tools and keeps only one popup open", () => {
    render(<OverviewToolDock/>);

    const toolbar = screen.getByRole("toolbar", { name: "Operations panels" });
    expect(within(toolbar).getAllByRole("button").map((button) => button.getAttribute("aria-label"))).toEqual([
      "Pause live updates",
      "Open operations statistics",
      "Open fleet",
      "Open alerts",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Open operations statistics" }));
    expect(screen.getByRole("dialog", { name: "Statistics" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open fleet" }));
    expect(screen.queryByRole("dialog", { name: "Statistics" })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Fleet · 2" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
