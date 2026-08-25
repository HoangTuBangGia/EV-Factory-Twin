import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "./login-form";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  login: vi.fn(),
  authState: {
    user: null as null | {
      id: string;
      email: string;
      display_name: string;
      role: "DESIGNER" | "MONITOR";
      is_active: boolean;
    },
    isLoading: false,
    error: null as string | null,
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
}));

vi.mock("@/components/auth/auth-provider", () => ({
  AuthActionError: class AuthActionError extends Error {},
  useAuth: () => ({ ...mocks.authState, login: mocks.login }),
}));

const designer = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "designer@example.com",
  display_name: "Demo Designer",
  role: "DESIGNER" as const,
  is_active: true,
};

const writeText = vi.fn();

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.authState.user = null;
    mocks.authState.isLoading = false;
    mocks.authState.error = null;
    writeText.mockReset();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
  });

  it("asks only for email and password, never a role", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("makes evaluator credentials easy to copy and use", async () => {
    writeText.mockResolvedValue(undefined);
    render(<LoginForm />);

    fireEvent.click(screen.getByRole("button", { name: "Use Designer account" }));
    expect(screen.getByLabelText("Email")).toHaveValue("designer@example.com");
    expect(screen.getByLabelText("Password")).toHaveValue("Designer123!");

    fireEvent.click(screen.getByRole("button", { name: "Copy Designer email" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("designer@example.com"));
    expect(screen.getByRole("button", { name: "Copy Designer email" })).toHaveTextContent(
      "Copied",
    );
  });

  it("signs in and sends a Designer to the scenario workspace", async () => {
    mocks.login.mockResolvedValue(designer);
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: designer.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "not-a-real-secret" } });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => expect(mocks.login).toHaveBeenCalledWith(designer.email, "not-a-real-secret"));
    expect(mocks.replace).toHaveBeenCalledWith("/scenarios");
    expect(mocks.refresh).toHaveBeenCalledOnce();
  });

  it("honors a safe return path after login", async () => {
    mocks.login.mockResolvedValue(designer);
    render(<LoginForm returnTo="/factory?robot=AMR-01" />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: designer.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "not-a-real-secret" } });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/factory?robot=AMR-01"));
  });

  it("shows a generic error when authentication fails", async () => {
    mocks.login.mockRejectedValue(new Error("internal provider details"));
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: designer.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to sign in. Please try again.");
    expect(screen.queryByText("internal provider details")).not.toBeInTheDocument();
  });
});
