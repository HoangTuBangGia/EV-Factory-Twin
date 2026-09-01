import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fixtureApplyCommand,
  fixtureLayoutVersion,
  fixtureScenario,
} from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { useToastStore } from "@/stores/toast-store";
import ScenariosPage from "./page";

const api = vi.hoisted(() => ({
  getBaselineScenario: vi.fn(),
  getLayouts: vi.fn(),
  getScenarios: vi.fn(),
  getCommands: vi.fn(),
  getLayout: vi.fn(),
  getLayoutVersion: vi.fn(),
  runScenario: vi.fn(),
  applyScenario: vi.fn(),
}));

const auth = vi.hoisted(() => ({
  id: "11111111-1111-4111-8111-111111111111",
  role: "DESIGNER" as "DESIGNER" | "MONITOR",
}));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({
    user: {
      id: auth.id,
      role: auth.role,
    },
  }),
}));
vi.mock("@/lib/api-client", () => ({ apiClient: api }));
vi.mock("@/components/scenarios/scenario-comparison", () => ({
  ScenarioComparison: () => <div>Metrics comparison</div>,
  ScenarioStatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));
vi.mock("@/components/scenarios/layout-comparison", () => ({
  LayoutComparison: () => <div>Layout comparison</div>,
}));
vi.mock("@/components/scenarios/optimization-panel", () => ({
  OptimizationPanel: () => <div>Optimization</div>,
}));
vi.mock("@/components/scenarios/scenario-actions", () => ({
  ScenarioActions: ({
    role,
    status,
    onStartRevision,
    onApply,
  }: {
    role: "DESIGNER" | "MONITOR";
    status: string;
    onStartRevision: () => void;
    onApply: () => void;
  }) => status === "REVISION_REQUESTED"
    ? <button type="button" onClick={onStartRevision}>Create revised candidate</button>
    : role === "MONITOR" && status === "APPROVED"
      ? <button type="button" onClick={onApply}>Apply to factory</button>
    : <div>Scenario actions</div>,
}));

const layoutSummary = {
  id: fixtureLayoutVersion.layout_id,
  name: fixtureLayoutVersion.name,
  latest_version: fixtureLayoutVersion.version,
  created_by: fixtureLayoutVersion.created_by,
  created_at: fixtureLayoutVersion.created_at,
  archived_at: null,
};

describe("ScenariosPage command history", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.id = "11111111-1111-4111-8111-111111111111";
    auth.role = "DESIGNER";
    useFactoryStore.getState().reset();
    useToastStore.setState({ toasts: [] });
    window.history.replaceState({}, "", "/scenarios");
    api.getBaselineScenario.mockResolvedValue(fixtureScenario);
    api.getLayouts.mockResolvedValue([layoutSummary]);
    api.getScenarios.mockResolvedValue([{ ...fixtureScenario, status: "APPROVED" }]);
    api.getCommands.mockResolvedValue([fixtureApplyCommand]);
    api.getLayout.mockResolvedValue(fixtureLayoutVersion);
    api.getLayoutVersion.mockResolvedValue(fixtureLayoutVersion);
    api.runScenario.mockResolvedValue(fixtureScenario);
    api.applyScenario.mockResolvedValue(fixtureApplyCommand);
  });

  it("hydrates the selected candidate timeline from durable commands", async () => {
    render(<ScenariosPage/>);

    await waitFor(() => expect(api.getCommands).toHaveBeenCalledOnce());
    expect(await screen.findByRole("region", { name: "Apply command status" }))
      .toHaveTextContent("PENDING");
    expect(screen.getByRole("link", { name: "Open technical details" }))
      .toHaveAttribute("href", "/commands");
  });

  it("keeps scenarios usable when supplemental command history fails", async () => {
    api.getCommands.mockRejectedValue(new Error("offline"));
    render(<ScenariosPage/>);

    expect(await screen.findByText(/Command history is unavailable: offline/)).toBeInTheDocument();
    expect(screen.getAllByText("candidate-01").length).toBeGreaterThan(0);
    expect(screen.getByText("Metrics comparison")).toBeInTheDocument();
  });

  it("selects a recommended candidate from the query string", async () => {
    const recommendation = {
      ...fixtureScenario,
      id: "SCN-OPT-01",
      name: "flow-option-01",
      created_at: "2026-08-14T00:01:00.000Z",
    };
    api.getScenarios.mockResolvedValue([fixtureScenario, recommendation]);
    window.history.replaceState({}, "", "/scenarios?candidate=SCN-OPT-01");

    render(<ScenariosPage/>);

    await waitFor(() => expect(api.getScenarios).toHaveBeenCalled());
    expect(screen.getAllByText("flow-option-01").length).toBeGreaterThan(0);
    expect(screen.getByText("SCN-OPT-01")).toBeInTheDocument();
  });

  it("reports the KPI summary when a simulation completes", async () => {
    render(<ScenariosPage/>);

    await waitFor(() => expect(screen.getByLabelText("Layout")).toHaveValue("LAYOUT-DEFAULT"));
    fireEvent.click(screen.getByRole("button", { name: "Run benchmark" }));

    await waitFor(() => expect(api.runScenario).toHaveBeenCalledOnce());
    expect(useToastStore.getState().toasts).toEqual([
      expect.objectContaining({
        type: "success",
        message: "Scenario \"candidate-01\" simulated · 355.0 tasks/h · 900.0s avg cycle · 3 starvation",
      }),
    ]);
  });

  it("prepares the original Designer's requested revision from its immutable layout", async () => {
    const requested = {
      ...fixtureScenario,
      status: "REVISION_REQUESTED" as const,
      review_note: "Move charging away from the aisle.",
      reviewed_at: "2026-08-14T00:05:00.000Z",
      reviewed_by: "22222222-2222-4222-8222-222222222222",
    };
    api.getScenarios.mockResolvedValue([requested]);
    window.scrollTo = vi.fn();

    render(<ScenariosPage/>);

    fireEvent.click(await screen.findByRole("button", { name: "Create revised candidate" }));
    await waitFor(() => expect(api.getLayoutVersion).toHaveBeenCalledWith(
      requested.config.layout_id,
      requested.config.layout_version,
    ));
    expect(screen.getByLabelText("Scenario name")).toHaveValue("candidate-01-revision");
    expect(screen.getAllByText("Move charging away from the aisle.")).toHaveLength(2);
  });

  it("applies an approved scenario only after styled confirmation", async () => {
    auth.id = "22222222-2222-4222-8222-222222222222";
    auth.role = "MONITOR";
    render(<ScenariosPage/>);

    const apply = await screen.findByRole("button", { name: "Apply to factory" });
    apply.focus();
    fireEvent.click(apply);
    const dialog = screen.getByRole("dialog", { name: /Apply "candidate-01" to the factory/ });
    expect(api.applyScenario).not.toHaveBeenCalled();
    expect(dialog).toHaveTextContent("factory runtime resets AMRs, tasks, alerts and metrics");

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(apply).toHaveFocus();

    fireEvent.click(apply);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole(
      "button",
      { name: "Apply to factory" },
    ));
    await waitFor(() => expect(api.applyScenario).toHaveBeenCalledWith(fixtureScenario.id, {
      timeout_seconds: 30,
      max_retries: 1,
    }));
  });
});
