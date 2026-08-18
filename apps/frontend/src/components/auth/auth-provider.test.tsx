import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Session } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth-provider";

const mocks = vi.hoisted(() => {
  class MockApiError extends Error {
    constructor(readonly status = 500) {
      super(`API ${status}`);
    }
  }
  return {
    ApiError: MockApiError,
    replace: vi.fn(),
    refresh: vi.fn(),
    getSession: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    getCurrentUser: vi.fn(),
    setApiAccessToken: vi.fn(),
    setApiUnauthorizedHandler: vi.fn(),
    unsubscribe: vi.fn(),
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
  usePathname: () => "/factory",
}));

vi.mock("@/lib/api-client", () => ({
  ApiError: mocks.ApiError,
  apiClient: { getCurrentUser: mocks.getCurrentUser },
  setApiAccessToken: mocks.setApiAccessToken,
  setApiUnauthorizedHandler: mocks.setApiUnauthorizedHandler,
}));

vi.mock("@/lib/supabase/client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession: mocks.getSession,
      signInWithPassword: mocks.signInWithPassword,
      signOut: mocks.signOut,
      onAuthStateChange: () => ({
        data: { subscription: { unsubscribe: mocks.unsubscribe } },
      }),
    },
  }),
}));

const session = {
  access_token: "restored-access-token",
  token_type: "bearer",
  expires_in: 3600,
  expires_at: 1_800_000_000,
  refresh_token: "refresh-token",
  user: {
    id: "11111111-1111-4111-8111-111111111111",
    app_metadata: {},
    user_metadata: {},
    aud: "authenticated",
    created_at: "2026-08-14T00:00:00Z",
  },
} as Session;

const currentUser = {
  id: session.user.id,
  email: "designer@example.com",
  display_name: "Demo Designer",
  role: "DESIGNER" as const,
  is_active: true,
};

function AuthProbe() {
  const { user, isLoading, logout } = useAuth();
  if (isLoading) return <span>loading</span>;
  return (
    <div>
      <span>{user?.display_name ?? "signed-out"}</span>
      <button type="button" onClick={() => void logout()}>logout</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getSession.mockResolvedValue({ data: { session }, error: null });
    mocks.getCurrentUser.mockResolvedValue(currentUser);
    mocks.signOut.mockResolvedValue({ error: null });
  });

  it("restores the cookie session and loads the trusted backend profile", async () => {
    render(<AuthProvider><AuthProbe /></AuthProvider>);

    expect(await screen.findByText("Demo Designer")).toBeInTheDocument();
    expect(mocks.setApiAccessToken).toHaveBeenCalledWith(session.access_token);
    expect(mocks.setApiUnauthorizedHandler).toHaveBeenCalledWith(expect.any(Function));
    expect(mocks.getCurrentUser).toHaveBeenCalledOnce();
  });

  it("clears the token and returns to login on logout", async () => {
    render(<AuthProvider><AuthProbe /></AuthProvider>);
    await screen.findByText("Demo Designer");
    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => expect(mocks.signOut).toHaveBeenCalledWith({ scope: "local" }));
    expect(mocks.setApiAccessToken).toHaveBeenLastCalledWith(null);
    expect(mocks.replace).toHaveBeenCalledWith("/login");
    expect(mocks.refresh).toHaveBeenCalledOnce();
  });

  it("marks an API 401 as an expired session and preserves the current route", async () => {
    render(<AuthProvider><AuthProbe /></AuthProvider>);
    await screen.findByText("Demo Designer");
    const handlerCall = mocks.setApiUnauthorizedHandler.mock.calls.find(
      ([handler]) => typeof handler === "function",
    );
    const handler = handlerCall?.[0] as (() => void) | undefined;

    expect(handler).toBeTypeOf("function");
    handler?.();

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith(
        "/login?reason=session_expired&returnTo=%2Ffactory",
      );
    });
    expect(mocks.setApiAccessToken).toHaveBeenLastCalledWith(null);
  });

  it("signs out locally and redirects when /auth/me reports an inactive profile", async () => {
    mocks.getCurrentUser.mockRejectedValue(new mocks.ApiError(403));

    render(<AuthProvider><AuthProbe /></AuthProvider>);

    expect(await screen.findByText("signed-out")).toBeInTheDocument();
    await waitFor(() => expect(mocks.signOut).toHaveBeenCalledWith({ scope: "local" }));
    expect(mocks.setApiAccessToken).toHaveBeenLastCalledWith(null);
    expect(mocks.replace).toHaveBeenCalledWith(
      "/login?reason=access_revoked&returnTo=%2Ffactory",
    );
  });
});
