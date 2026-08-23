import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApplicationFrame } from "./application-frame";

let pathname = "/";

vi.mock("next/navigation", () => ({ usePathname: () => pathname }));
vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { id: "user-1" }, isLoading: false, error: null }),
}));
vi.mock("@/components/layout/data-provider", () => ({ DataProvider: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("@/components/layout/sidebar", () => ({ Sidebar: () => <div>navigation toggle</div> }));
vi.mock("@/components/layout/topbar", () => ({ Topbar: () => <div>application topbar</div> }));

describe("ApplicationFrame", () => {
  beforeEach(() => { pathname = "/"; });

  it("gives Overview the full viewport and keeps the standard frame on other routes", () => {
    const { rerender } = render(<ApplicationFrame><div>page content</div></ApplicationFrame>);

    expect(screen.queryByText("application topbar")).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("cockpit-content");

    pathname = "/fleet";
    rerender(<ApplicationFrame><div>page content</div></ApplicationFrame>);
    expect(screen.getByText("application topbar")).toBeInTheDocument();
    expect(screen.getByRole("main")).not.toHaveClass("cockpit-content");
  });
});
