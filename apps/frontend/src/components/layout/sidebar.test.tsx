import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "./sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));
vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({
    user: { display_name: "Demo Designer", role: "DESIGNER" },
    logout: vi.fn(),
  }),
}));
vi.mock("@/stores/factory-store", () => ({
  useFactoryStore: (select: (state: unknown) => unknown) => select({ connectionStatus: "LIVE" }),
}));

describe("Sidebar", () => {
  it("opens as a dropdown and closes on an outside click", () => {
    render(<Sidebar/>);

    expect(screen.queryByRole("navigation", { name: "Application navigation" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getByRole("navigation", { name: "Application navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");

    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("navigation", { name: "Application navigation" })).not.toBeInTheDocument();
  });
});
