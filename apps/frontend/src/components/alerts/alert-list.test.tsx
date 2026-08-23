import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { fixtureAlerts } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { AlertList } from "./alert-list";

describe("AlertList", () => {
  beforeEach(() => useFactoryStore.getState().reset());

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
    expect(screen.getByText("No active alerts.")).toBeInTheDocument();
  });
});
