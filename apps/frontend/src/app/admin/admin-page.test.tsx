import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminPage from "./page";

const mocks = vi.hoisted(() => {
  class MockApiError extends Error {
    constructor(readonly status: number) {
      super(`API ${status}`);
    }
  }
  return {
    ApiError: MockApiError,
    authState: {
      user: null as null | {
        id: string;
        email: string;
        display_name: string;
        role: "DESIGNER" | "MONITOR" | "ADMIN";
        is_active: boolean;
      },
    },
    getAdminUsers: vi.fn(),
    getAdminAudit: vi.fn(),
    updateAdminUser: vi.fn(),
    inviteAdminUser: vi.fn(),
  };
});

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => mocks.authState,
}));

vi.mock("@/lib/api-client", () => ({
  ApiError: mocks.ApiError,
  apiClient: {
    getAdminUsers: mocks.getAdminUsers,
    getAdminAudit: mocks.getAdminAudit,
    updateAdminUser: mocks.updateAdminUser,
    inviteAdminUser: mocks.inviteAdminUser,
  },
}));

const admin = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "admin@example.com",
  display_name: "Factory Admin",
  role: "ADMIN" as const,
  is_active: true,
};

const managedUser = {
  id: "22222222-2222-4222-8222-222222222222",
  email: "designer@example.com",
  display_name: "Demo Designer",
  role: "DESIGNER" as const,
  is_active: true,
  created_at: "2026-08-14T00:00:00.000Z",
};

const auditEvent = {
  id: 1,
  actor_id: admin.id,
  actor_role: "ADMIN" as const,
  action: "ROLE_CHANGED",
  resource_type: "profile",
  resource_id: managedUser.id,
  before_data: { role: "MONITOR" },
  after_data: { role: "DESIGNER" },
  request_id: "33333333-3333-4333-8333-333333333333",
  created_at: "2026-08-14T00:05:00.000Z",
};

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.authState.user = admin;
    mocks.getAdminUsers.mockResolvedValue([managedUser]);
    mocks.getAdminAudit.mockResolvedValue([auditEvent]);
    mocks.updateAdminUser.mockImplementation(async (_id, update) => ({
      ...managedUser,
      ...update,
    }));
    mocks.inviteAdminUser.mockImplementation(async (invite) => ({
      ...managedUser,
      ...invite,
      id: "44444444-4444-4444-8444-444444444444",
    }));
  });

  it("shows a clear 403 and makes no admin requests for a non-admin", () => {
    mocks.authState.user = { ...admin, role: "MONITOR" };
    render(<AdminPage />);

    expect(screen.getByText("403 Forbidden")).toBeInTheDocument();
    expect(screen.getByText(/Administrator access required/i)).toBeInTheDocument();
    expect(mocks.getAdminUsers).not.toHaveBeenCalled();
    expect(mocks.getAdminAudit).not.toHaveBeenCalled();
  });

  it("loads users and audit data without rendering a password field", async () => {
    render(<AdminPage />);

    expect(await screen.findByText("designer@example.com")).toBeInTheDocument();
    expect(screen.getByText("ROLE_CHANGED")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Display name")).toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    expect(screen.getByText(/ADMIN is read-only for factory operations/i)).toBeInTheDocument();
  });

  it("edits a user role through the PATCH contract", async () => {
    render(<AdminPage />);
    const role = await screen.findByLabelText("Role for Demo Designer");

    fireEvent.change(role, { target: { value: "MONITOR" } });

    await waitFor(() => expect(mocks.updateAdminUser).toHaveBeenCalledWith(
      managedUser.id,
      { role: "MONITOR" },
    ));
  });

  it("submits an invitation without a password", async () => {
    render(<AdminPage />);
    await screen.findByText("designer@example.com");
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "monitor@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "New Monitor" },
    });
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "MONITOR" } });
    fireEvent.click(screen.getByRole("button", { name: "Invite user" }));

    await waitFor(() => expect(mocks.inviteAdminUser).toHaveBeenCalledWith({
      email: "monitor@example.com",
      display_name: "New Monitor",
      role: "MONITOR",
    }));
    expect(mocks.inviteAdminUser.mock.calls[0]?.[0]).not.toHaveProperty("password");
  });

  it("explains when server-side invitation support is unavailable", async () => {
    mocks.inviteAdminUser.mockRejectedValue(new mocks.ApiError(503));
    render(<AdminPage />);
    await screen.findByText("designer@example.com");
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "New User" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite user" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /server-side Supabase Admin integration is not configured/i,
    );
  });
});
