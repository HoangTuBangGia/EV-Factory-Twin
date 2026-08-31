import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureLayoutVersion, fixtureScenario } from "@/lib/fixtures";
import type { LayoutVersion } from "@/schemas/layout";
import type { Scenario } from "@/schemas/scenario";
import { useFactoryStore } from "@/stores/factory-store";
import { LayoutComparison } from "./layout-comparison";

const api = vi.hoisted(() => ({ getLayoutVersion: vi.fn() }));

vi.mock("@/lib/api-client", () => ({ apiClient: api }));
vi.mock("@/components/factory/factory-plant-map-2d", () => ({
  FactoryPlantMap2D: ({ layout }: { layout: { id: string; version: number } }) => (
    <div>map {layout.id} v{layout.version}</div>
  ),
}));

function scenario(overrides: Partial<Scenario>, config: Partial<Scenario["config"]> = {}): Scenario {
  return {
    ...fixtureScenario,
    ...overrides,
    config: { ...fixtureScenario.config, ...config },
  };
}

function version(overrides: Partial<LayoutVersion> = {}): LayoutVersion {
  return { ...fixtureLayoutVersion, ...overrides };
}

/** jsdom does not run the summary activation behaviour, so open it directly. */
function expand() {
  const details = screen.getByRole("group");
  if (!(details instanceof HTMLDetailsElement)) throw new Error("comparison is not a details");
  details.open = true;
  details.dispatchEvent(new Event("toggle"));
}

beforeEach(() => {
  useFactoryStore.getState().reset();
  vi.clearAllMocks();
  api.getLayoutVersion.mockImplementation(async (id: string, requested: number) => (
    version({ layout_id: id, version: requested })
  ));
});

describe("LayoutComparison", () => {
  const applied = scenario(
    { id: "SCN-APPLIED", status: "APPLIED", applied_at: "2026-08-14T02:00:00.000Z" },
    { layout_version: 1 },
  );
  const candidate = scenario({ id: "SCN-CANDIDATE" }, { layout_version: 2 });

  it("fetches nothing until the panel is expanded", () => {
    useFactoryStore.getState().setScenarios([applied, candidate]);
    render(<LayoutComparison candidate={candidate}/>);

    expect(screen.getByText("Layout change · LAYOUT-DEFAULT v1 → LAYOUT-DEFAULT v2"))
      .toBeInTheDocument();
    expect(api.getLayoutVersion).not.toHaveBeenCalled();
  });

  it("shows both revisions and what physically changed", async () => {
    api.getLayoutVersion.mockImplementation(async (id: string, requested: number) => version({
      layout_id: id,
      version: requested,
      config: {
        ...fixtureLayoutVersion.config,
        charger_count: requested === 2 ? 4 : 2,
      },
    }));
    useFactoryStore.getState().setScenarios([applied, candidate]);
    render(<LayoutComparison candidate={candidate}/>);

    expand();

    expect(await screen.findByText("map LAYOUT-DEFAULT v1")).toBeInTheDocument();
    expect(screen.getByText("map LAYOUT-DEFAULT v2")).toBeInTheDocument();
    expect(screen.getByText("Charger count")).toBeInTheDocument();
    expect(screen.getByText("2 → 4")).toBeInTheDocument();
  });

  it("says the candidate reuses the live geometry and loads it once", async () => {
    const sameGeometry = scenario({ id: "SCN-SAME" }, { layout_version: 1 });
    useFactoryStore.getState().setScenarios([applied, sameGeometry]);
    render(<LayoutComparison candidate={sameGeometry}/>);

    expand();

    expect(await screen.findByText(/reuses the live geometry/)).toBeInTheDocument();
    expect(api.getLayoutVersion).toHaveBeenCalledOnce();
  });

  it("explains that an unapplied factory has no comparison base", async () => {
    useFactoryStore.getState().setScenarios([candidate]);
    render(<LayoutComparison candidate={candidate}/>);

    expand();

    expect(await screen.findByText(/nothing to compare against/)).toBeInTheDocument();
    expect(screen.queryByText("map LAYOUT-DEFAULT v1")).not.toBeInTheDocument();
  });

  it("keeps the review usable when geometry cannot be loaded", async () => {
    api.getLayoutVersion.mockRejectedValue(new Error("offline"));
    useFactoryStore.getState().setScenarios([applied, candidate]);
    render(<LayoutComparison candidate={candidate}/>);

    expand();

    await waitFor(() => expect(screen.getByText(/geometry is unavailable/)).toBeInTheDocument());
  });
});
