import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fixtureApplyCommand,
  fixtureLayoutVersion,
  fixtureScenario,
} from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import ScenariosPage from "./page";

const api = vi.hoisted(() => ({
  getBaselineScenario: vi.fn(),
  getLayouts: vi.fn(),
  getScenarios: vi.fn(),
  getCommands: vi.fn(),
  getLayout: vi.fn(),
  getLayoutVersion: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({
    user: {
      id: "11111111-1111-4111-8111-111111111111",
      role: "DESIGNER",
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
  ScenarioActions: () => <div>Scenario actions</div>,
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
    useFactoryStore.getState().reset();
    window.history.replaceState({}, "", "/scenarios");
    api.getBaselineScenario.mockResolvedValue(fixtureScenario);
    api.getLayouts.mockResolvedValue([layoutSummary]);
    api.getScenarios.mockResolvedValue([{ ...fixtureScenario, status: "APPROVED" }]);
    api.getCommands.mockResolvedValue([fixtureApplyCommand]);
    api.getLayout.mockResolvedValue(fixtureLayoutVersion);
    api.getLayoutVersion.mockResolvedValue(fixtureLayoutVersion);
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
});
