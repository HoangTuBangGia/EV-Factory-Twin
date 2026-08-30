import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useFactoryStore } from "@/stores/factory-store";
import { ConnectionBanner } from "./connection-banner";

describe("ConnectionBanner", () => {
  beforeEach(() => useFactoryStore.getState().reset());

  it("warns when live data is offline and reconnects on request", () => {
    const reconnect = vi.fn();
    render(<ConnectionBanner onReconnect={reconnect}/>);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Live data disconnected. Displayed data may be stale.");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    fireEvent.click(screen.getByRole("button", { name: "Reconnect" }));
    expect(reconnect).toHaveBeenCalledOnce();
  });

  it("shows non-interactive reconnect progress", () => {
    useFactoryStore.getState().setConnectionStatus("CONNECTING");
    render(<ConnectionBanner onReconnect={vi.fn()}/>);

    expect(screen.getByRole("status")).toHaveTextContent("Reconnecting…");
    expect(screen.getByRole("button", { name: "Reconnect" })).toBeDisabled();
  });

  it.each(["LIVE", "MOCK"] as const)("stays hidden when status is %s", (status) => {
    useFactoryStore.getState().setConnectionStatus(status);
    const { container } = render(<ConnectionBanner onReconnect={vi.fn()}/>);
    expect(container).toBeEmptyDOMElement();
  });
});
