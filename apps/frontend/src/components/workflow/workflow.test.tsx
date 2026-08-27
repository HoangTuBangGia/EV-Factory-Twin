import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureApplyCommand, fixtureScenario } from "@/lib/fixtures";
import type { Command } from "@/schemas/command";
import { useFactoryStore } from "@/stores/factory-store";
import { NextActionStrip } from "./next-action-strip";
import { WorkflowTimeline } from "./workflow-timeline";

const DESIGNER_ID = fixtureScenario.created_by ?? "";
const MONITOR_ID = "22222222-2222-4222-8222-222222222222";

const auth = vi.hoisted(() => ({
  user: null as { id: string; role: "DESIGNER" | "MONITOR" } | null,
}));
const api = vi.hoisted(() => ({ getScenarios: vi.fn() }));

vi.mock("@/components/auth/auth-provider", () => ({ useAuth: () => ({ user: auth.user }) }));
vi.mock("@/lib/api-client", () => ({ apiClient: api }));

function command(status: Command["status"], acknowledged = false): Command {
  return {
    ...fixtureApplyCommand,
    status,
    attempts: [{
      ...fixtureApplyCommand.attempts[0],
      status,
      acknowledged_at: acknowledged ? "2026-08-14T00:10:05.000Z" : null,
    }],
  };
}

beforeEach(() => {
  auth.user = { id: DESIGNER_ID, role: "DESIGNER" };
  useFactoryStore.getState().reset();
  api.getScenarios.mockResolvedValue([]);
});

describe("WorkflowTimeline", () => {
  const stages = () => screen.getByRole("list", { name: "Candidate review progress" });

  it("closes the passed stages and highlights the live one", () => {
    render(<WorkflowTimeline status="APPROVED" />);

    const items = within(stages()).getAllByRole("listitem");
    expect(items.map((item) => item.className)).toEqual(["done", "done", "current", "pending"]);
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(screen.queryByRole("list", { name: "Apply progress" })).not.toBeInTheDocument();
  });

  it("shows review as rejected and explains that the status is terminal", () => {
    render(<WorkflowTimeline status="REJECTED" />);

    expect(within(stages()).getAllByRole("listitem")[1]).toHaveClass("rejected");
    expect(screen.getByText(/cannot be resubmitted/)).toBeInTheDocument();
  });

  it("tracks the apply phases separately from the review stages", () => {
    render(<WorkflowTimeline status="APPROVED" command={command("ACKNOWLEDGED", true)} />);

    const phases = within(screen.getByRole("list", { name: "Apply progress" }));
    expect(phases.getAllByRole("listitem").map((item) => item.className))
      .toEqual(["done", "current", "pending"]);
  });

  it("says the runtime is unchanged when the bridge never completed the command", () => {
    render(<WorkflowTimeline status="APPROVED" command={command("TIMED_OUT")} />);

    expect(screen.getByText(/factory runtime is unchanged/)).toBeInTheDocument();
  });
});

describe("NextActionStrip", () => {
  it("tells a designer that a simulated candidate still needs submitting", async () => {
    api.getScenarios.mockResolvedValue([fixtureScenario]);
    render(<NextActionStrip />);

    expect(await screen.findByText("candidate-01 is simulated but not submitted"))
      .toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open my candidates" }))
      .toHaveAttribute("href", "/scenarios?queue=mine");
  });

  it("points a monitor at the review queue and shares the loaded candidates", async () => {
    auth.user = { id: MONITOR_ID, role: "MONITOR" };
    api.getScenarios.mockResolvedValue([{ ...fixtureScenario, status: "SUBMITTED" as const }]);
    render(<NextActionStrip floating />);

    expect(await screen.findByText("1 candidate awaiting your review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open review queue" }))
      .toHaveAttribute("href", "/scenarios?queue=awaiting");
    expect(screen.getByRole("complementary", { name: "Next step" })).toHaveClass("floating");
    expect(useFactoryStore.getState().scenarios).toHaveLength(1);
  });

  it("stays hidden when the candidate list cannot be loaded", async () => {
    api.getScenarios.mockRejectedValue(new Error("offline"));
    const { container } = render(<NextActionStrip />);

    await waitFor(() => expect(api.getScenarios).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
