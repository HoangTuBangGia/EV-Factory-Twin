import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import FactoryPage from "./page";

const mapSpy = vi.hoisted(() => vi.fn());
const apiMocks = vi.hoisted(() => ({
  getScenarios: vi.fn().mockResolvedValue([]),
  getLayoutVersion: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: "DESIGNER" } }),
}));

vi.mock("@/lib/api-client", () => ({ apiClient: apiMocks }));

vi.mock("@/components/factory/factory-map", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/components/factory/factory-map")>();
  return {
    ...actual,
    FactoryMap: (props: unknown) => {
      mapSpy(props);
      return <div data-testid="factory-map"/>;
    },
  };
});

vi.mock("@/components/alerts/alert-list", () => ({ AlertList: () => null }));
vi.mock("@/components/fleet/robot-drawer", () => ({ RobotDrawer: () => null }));

describe("FactoryPage", () => {
  it("uses the 2D view and controls visible layers", () => {
    render(<FactoryPage/>);

    expect(screen.getByText(/Realtime AMR overlays on reference 2D factory geometry/i)).toBeInTheDocument();
    expect(mapSpy.mock.lastCall?.[0]).toHaveProperty("view", "2d");
    expect(mapSpy.mock.lastCall?.[0]).toHaveProperty("twoDimensionalVariant", "plant");
    expect(mapSpy.mock.lastCall?.[0]).toMatchObject({
      layers: { stations: true, routes: true, noGoZones: true, congestionZones: true },
    });

    fireEvent.click(screen.getByRole("button", { name: "Routes" }));
    expect(screen.getByRole("button", { name: "Routes" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(mapSpy.mock.lastCall?.[0]).toMatchObject({ layers: { routes: false } });

    fireEvent.click(screen.getByRole("button", { name: "All layers" }));
    expect(mapSpy.mock.lastCall?.[0]).toMatchObject({
      layers: { stations: true, routes: true, noGoZones: true, congestionZones: true },
    });

    fireEvent.click(screen.getByRole("button", { name: "Congestion zones" }));
    expect(mapSpy.mock.lastCall?.[0]).toMatchObject({ layers: { congestionZones: false } });
  });
});
