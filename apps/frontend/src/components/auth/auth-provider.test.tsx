import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth-provider";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(), refresh: vi.fn(), login: vi.fn(), logout: vi.fn(),
  getCurrentUser: vi.fn(), setApiAccessToken: vi.fn(), setApiUnauthorizedHandler: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
  usePathname: () => "/factory",
}));
vi.mock("@/lib/api-client", () => ({
  ApiError: class extends Error { constructor(readonly status = 500) { super(); } },
  apiClient: { login: mocks.login, logout: mocks.logout, getCurrentUser: mocks.getCurrentUser },
  setApiAccessToken: mocks.setApiAccessToken,
  setApiUnauthorizedHandler: mocks.setApiUnauthorizedHandler,
}));

const currentUser = {
  id: "11111111-1111-4111-8111-111111111111", email: "designer@example.com",
  display_name: "Demo Designer", role: "DESIGNER" as const, is_active: true,
};

function AuthProbe() {
  const { user, isLoading, login, logout } = useAuth();
  if (isLoading) return <span>loading</span>;
  return <div>
    <span>{user?.display_name ?? "signed-out"}</span>
    <button type="button" onClick={() => void login("designer@example.com", "password")}>login</button>
    <button type="button" onClick={() => void logout()}>logout</button>
  </div>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mocks.login.mockResolvedValue({ access_token: "backend-access-token", token_type: "bearer", expires_at: 1_800_000_000, user: currentUser });
    mocks.logout.mockResolvedValue(undefined);
  });

  it("signs in through the backend and stores the token for this tab", async () => {
    render(<AuthProvider><AuthProbe /></AuthProvider>);
    await screen.findByText("signed-out");
    fireEvent.click(screen.getByRole("button", { name: "login" }));
    expect(await screen.findByText("Demo Designer")).toBeInTheDocument();
    expect(sessionStorage.getItem("ev-twin-access-token")).toBe("backend-access-token");
  });

  it("restores a backend token and loads the trusted profile", async () => {
    sessionStorage.setItem("ev-twin-access-token", "restored-token");
    mocks.getCurrentUser.mockResolvedValue(currentUser);
    render(<AuthProvider><AuthProbe /></AuthProvider>);
    expect(await screen.findByText("Demo Designer")).toBeInTheDocument();
    expect(mocks.setApiAccessToken).toHaveBeenCalledWith("restored-token");
  });

  it("clears local auth even if the stateless logout request fails", async () => {
    sessionStorage.setItem("ev-twin-access-token", "restored-token");
    mocks.getCurrentUser.mockResolvedValue(currentUser);
    mocks.logout.mockRejectedValue(new Error("offline"));
    render(<AuthProvider><AuthProbe /></AuthProvider>);
    await screen.findByText("Demo Designer");
    fireEvent.click(screen.getByRole("button", { name: "logout" }));
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/login"));
    expect(sessionStorage.getItem("ev-twin-access-token")).toBeNull();
  });
});
