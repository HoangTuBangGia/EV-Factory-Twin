import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import { fixtureAlerts } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { useToastStore } from "@/stores/toast-store";
import { AlertList } from "./alert-list";

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: "MONITOR" } }),
}));
vi.mock("@/lib/api-client", () => ({ apiClient: { acknowledgeAlert: vi.fn() } }));

describe("AlertList", () => {
  beforeEach(() => {
    useFactoryStore.getState().reset();
    useToastStore.setState({ toasts: [] });
    vi.clearAllMocks();
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

  it("keeps fixture acknowledgement local without calling the API", () => {
    useFactoryStore.getState().setAlerts(fixtureAlerts);
    render(<AlertList/>);

    fireEvent.click(screen.getByRole("button", { name: "Acknowledge WARNING LOW_BATTERY" }));
    expect(screen.queryByText("AMR-05 battery below 20%")).not.toBeInTheDocument();
    expect(useFactoryStore.getState().acknowledgedAlertIds).toEqual([fixtureAlerts[0].id]);
    expect(apiClient.acknowledgeAlert).not.toHaveBeenCalled();
    expect(useToastStore.getState().toasts).toEqual([expect.objectContaining({
      type: "info", message: "Acknowledged in fixture mode",
    })]);

    fireEvent.click(screen.getByRole("checkbox", { name: "Show acknowledged" }));
    const alert = screen.getByText("AMR-05 battery below 20%").closest("article")!;
    expect(within(alert).getByText("Acknowledged in fixture mode")).toBeInTheDocument();
    expect(within(alert).queryByRole("button", { name: /Acknowledge/ })).not.toBeInTheDocument();
  });

  it("persists acknowledgement through the API and stores the server result", async () => {
    const active = fixtureAlerts[0];
    const acknowledged = {
      ...active,
      acknowledged_at: "2026-08-11T04:01:00.000Z",
      acknowledged_by: "22222222-2222-4222-8222-222222222222",
    };
    vi.mocked(apiClient.acknowledgeAlert).mockResolvedValue(acknowledged);
    useFactoryStore.getState().setAlerts([active]);
    render(<AlertList fixtureMode={false}/>);

    fireEvent.click(screen.getByRole("button", { name: "Acknowledge WARNING LOW_BATTERY" }));

    await waitFor(() => expect(apiClient.acknowledgeAlert).toHaveBeenCalledWith(active.id));
    expect(useFactoryStore.getState().alerts[0]).toEqual(acknowledged);
    expect(screen.queryByText(active.message)).not.toBeInTheDocument();
    expect(useToastStore.getState().toasts).toEqual([expect.objectContaining({
      type: "success", message: "Alert acknowledged",
    })]);
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
