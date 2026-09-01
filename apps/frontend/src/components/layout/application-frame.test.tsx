import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApplicationFrame } from "./application-frame";

const mocks = vi.hoisted(() => ({ replace: vi.fn() }));
let pathname = "/";
let authState = { user: { id: "user-1" } as { id: string } | null, isLoading: false, error: null as string | null };

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace: mocks.replace }),
}));
vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ ...authState, logout: vi.fn(), refreshUser: vi.fn() }),
}));
vi.mock("@/components/layout/data-provider", () => ({ DataProvider: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("@/components/layout/sidebar", () => ({ Sidebar: () => <div>navigation toggle</div> }));
vi.mock("@/components/layout/topbar", () => ({ Topbar: () => <div>application topbar</div> }));
vi.mock("@/components/onboarding/onboarding-tour", () => ({
  OnboardingTour: () => <div>onboarding tour</div>,
}));
vi.mock("@/components/workflow/next-action-strip", () => ({
  NextActionStrip: ({ floating }: { floating?: boolean }) => (
    <div>next step strip{floating ? " floating" : ""}</div>
  ),
}));

describe("ApplicationFrame", () => {
  beforeEach(() => {
    pathname = "/";
    authState = { user: { id: "user-1" }, isLoading: false, error: null };
    mocks.replace.mockReset();
    window.history.replaceState({}, "", "/");
  });

  it("gives Overview the full viewport and keeps the standard frame on other routes", () => {
    const { rerender } = render(<ApplicationFrame><div>page content</div></ApplicationFrame>);

    expect(screen.queryByText("application topbar")).not.toBeInTheDocument();
    expect(screen.getByText("onboarding tour")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("cockpit-content");
    expect(screen.getByText("next step strip floating")).toBeInTheDocument();

    pathname = "/fleet";
    rerender(<ApplicationFrame><div>page content</div></ApplicationFrame>);
    expect(screen.getByText("application topbar")).toBeInTheDocument();
    expect(screen.getByRole("main")).not.toHaveClass("cockpit-content");
    expect(screen.getByText("next step strip")).toBeInTheDocument();
  });

  it("redirects a signed-out direct route and preserves its return path", async () => {
    pathname = "/factory";
    authState = { user: null, isLoading: false, error: null };
    window.history.replaceState({}, "", "/factory?robot=AMR-01");

    render(<ApplicationFrame><div>protected content</div></ApplicationFrame>);

    expect(screen.getByRole("main")).toHaveTextContent("Redirecting to login…");
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(
      "/login?returnTo=%2Ffactory%3Frobot%3DAMR-01",
    ));
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});
