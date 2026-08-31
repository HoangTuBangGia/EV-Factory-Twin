import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { CurrentUser } from "@/schemas/auth";
import { OnboardingTour } from "./onboarding-tour";

const designer: CurrentUser = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "designer@example.com",
  display_name: "Demo Designer",
  role: "DESIGNER",
  is_active: true,
};

const monitor: CurrentUser = {
  ...designer,
  id: "22222222-2222-4222-8222-222222222222",
  email: "monitor@example.com",
  display_name: "Demo Monitor",
  role: "MONITOR",
};

describe("OnboardingTour", () => {
  beforeEach(() => localStorage.clear());

  it("completes and persists the four-step Designer tour", async () => {
    const { unmount } = render(<OnboardingTour user={designer}/>);
    expect(await screen.findByRole("dialog")).toHaveAccessibleName("EV Factory Digital Twin");

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Designer");
    expect(screen.getByRole("link", { name: /Open layout editor/ })).toHaveAttribute("href", "/layouts");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Live operations at a glance");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Build a candidate");
    fireEvent.click(screen.getByRole("button", { name: "Get started" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(localStorage.getItem(`ft-onboarding-done:${designer.id}`)).toBe("1");
    unmount();
    render(<OnboardingTour user={designer}/>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows Monitor-specific responsibility and destination", async () => {
    render(<OnboardingTour user={monitor}/>);
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("dialog")).toHaveAccessibleName("Monitor");
    expect(screen.getByText(/Review submitted candidates/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open review queue/ }))
      .toHaveAttribute("href", "/scenarios?queue=awaiting");
  });

  it("does not persist a skipped tour when the preference is cleared", async () => {
    const { unmount } = render(<OnboardingTour user={designer}/>);
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("checkbox", { name: "Don't show this tour again" }));
    fireEvent.click(screen.getByRole("button", { name: "Skip tour" }));

    expect(localStorage.getItem(`ft-onboarding-done:${designer.id}`)).toBeNull();
    unmount();
    render(<OnboardingTour user={designer}/>);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("traps focus, closes on Escape, and restores prior focus", async () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    render(<OnboardingTour user={designer}/>);
    await screen.findByRole("dialog");

    expect(screen.getByRole("heading", { name: "EV Factory Digital Twin" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("checkbox", { name: "Don't show this tour again" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
    opener.remove();
  });
});
