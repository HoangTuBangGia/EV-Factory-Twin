import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { fixtureAlerts } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { useToastStore } from "@/stores/toast-store";
import { AlertList } from "./alert-list";

describe("AlertList", () => {
  beforeEach(() => {
    useFactoryStore.getState().reset();
    useToastStore.setState({ toasts: [] });
  });

  it("removes a cleared alert after its realtime lifecycle update", () => {
    const active = fixtureAlerts[0];
    useFactoryStore.getState().setAlerts([active]);
    const { rerender } = render(<AlertList />);
    expect(screen.getByText(active.message)).toBeInTheDocument();

    useFactoryStore.getState().addAlert({
      ...active,
      status: "CLEARED",
      last_seen_at: "2026-08-11T04:01:00.000Z",
      cleared_at: "2026-08-11T04:01:00.000Z",
    });
    rerender(<AlertList />);

    expect(screen.queryByText(active.message)).not.toBeInTheDocument();
    expect(screen.getByText("No matching active alerts.")).toBeInTheDocument();
  });

  it("filters by severity and searches robot, task, or message", () => {
    useFactoryStore.getState().setAlerts(fixtureAlerts);
    render(<AlertList/>);

    fireEvent.click(screen.getByRole("button", { name: "Critical" }));
    expect(screen.getByText("Marriage Station supply risk detected")).toBeInTheDocument();
    expect(screen.queryByText("AMR-05 battery below 20%")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    const search = screen.getByRole("searchbox", { name: "Search alerts" });
    fireEvent.change(search, { target: { value: "AMR-05" } });
    expect(screen.getByText("AMR-05 battery below 20%")).toBeInTheDocument();
    expect(screen.queryByText("Battery task backlog detected")).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "TASK-102" } });
    expect(screen.getByText("Battery task backlog detected")).toBeInTheDocument();
    fireEvent.change(search, { target: { value: "supply risk" } });
    expect(screen.getByText("Marriage Station supply risk detected")).toBeInTheDocument();
  });

  it("acknowledges locally, hides the alert, and can show it again", () => {
    useFactoryStore.getState().setAlerts(fixtureAlerts);
    render(<AlertList/>);

    fireEvent.click(screen.getByRole("button", { name: "Acknowledge WARNING LOW_BATTERY" }));
    expect(screen.queryByText("AMR-05 battery below 20%")).not.toBeInTheDocument();
    expect(useFactoryStore.getState().acknowledgedAlertIds).toEqual([fixtureAlerts[0].id]);
    expect(useToastStore.getState().toasts).toEqual([
      expect.objectContaining({ type: "info", message: "Acknowledged locally" }),
    ]);

    fireEvent.click(screen.getByRole("checkbox", { name: "Show acknowledged" }));
    const alert = screen.getByText("AMR-05 battery below 20%").closest("article")!;
    expect(within(alert).getByText("Acknowledged locally")).toBeInTheDocument();
    expect(within(alert).queryByRole("button", { name: /Acknowledge/ })).not.toBeInTheDocument();
  });

  it("sorts newest first by default and can prioritize severity", () => {
    useFactoryStore.getState().setAlerts([
      { ...fixtureAlerts[0], timestamp: "2026-08-11T04:03:00.000Z" },
      { ...fixtureAlerts[1], timestamp: "2026-08-11T04:02:00.000Z" },
      { ...fixtureAlerts[2], timestamp: "2026-08-11T04:01:00.000Z" },
    ]);
    render(<AlertList/>);

    expect(within(screen.getAllByRole("article")[0]).getByText(/WARNING/)).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Sort alerts" }), {
      target: { value: "severity" },
    });
    expect(within(screen.getAllByRole("article")[0]).getByText(/CRITICAL/)).toBeInTheDocument();
  });
});
