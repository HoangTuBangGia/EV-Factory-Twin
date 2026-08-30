import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureScenario } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { useToastStore } from "@/stores/toast-store";
import LayoutsPage from "./page";

const state = vi.hoisted(() => ({ role: "DESIGNER" as "DESIGNER" | "MONITOR" }));
const api = vi.hoisted(() => ({
  getLayouts: vi.fn().mockResolvedValue([]),
  getLayout: vi.fn(),
  createLayout: vi.fn(),
  createLayoutVersion: vi.fn(),
  renameLayout: vi.fn(),
  archiveLayout: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: state.role } }),
}));
vi.mock("@/lib/api-client", () => ({ apiClient: api }));

const savedLayout = async (request: { name: string; content: object }) => ({
  ...request.content,
  layout_id: "LAYOUT-0001",
  name: request.name,
  version: 1,
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-08-24T00:00:00Z",
  archived_at: null,
});

describe("LayoutsPage", () => {
  beforeEach(() => {
    state.role = "DESIGNER";
    useFactoryStore.getState().reset();
    useToastStore.setState({ toasts: [] });
    api.getLayouts.mockResolvedValue([]);
    vi.clearAllMocks();
  });

  it("updates station coordinates in the validated preview", () => {
    const { container } = render(<LayoutsPage/>);
    const xInput = screen.getByLabelText("X (m)", { selector: "#BATTERY_BUFFER-x" });

    fireEvent.change(xInput, { target: { value: "4.2" } });
    expect(xInput).toHaveValue(4);
    expect(container.querySelector('.fm-zone circle[cx="4"]')).toBeInTheDocument();
  });

  it("creates a persisted layout from a valid draft", async () => {
    api.createLayout.mockImplementation(savedLayout);
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    await waitFor(() => expect(api.createLayout).toHaveBeenCalledOnce());
    expect(api.createLayout.mock.calls[0]?.[0]).toMatchObject({
      name: "Battery logistics candidate",
      content: {
        config: { robot_count: 5 },
        congestion_zones: [{ id: "WAREHOUSE_PRODUCTION_DOOR" }],
      },
    });
    expect(await screen.findByText("Created LAYOUT-0001.")).toBeInTheDocument();
    expect(useToastStore.getState().toasts).toEqual([
      expect.objectContaining({ type: "success", message: "Created LAYOUT-0001." }),
    ]);
  });

  it("keeps the save error in context and raises an error toast", async () => {
    api.createLayout.mockRejectedValue(new Error("database unavailable"));
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    expect(await screen.findByText("Unable to save layout: database unavailable")).toBeInTheDocument();
    expect(useToastStore.getState().toasts).toEqual([
      expect.objectContaining({
        type: "error",
        message: "Unable to save layout: database unavailable",
      }),
    ]);
  });

  it("draws the battery route by selecting its endpoint stations", () => {
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Draw selected route" }));
    fireEvent.pointerDown(screen.getByRole("button", { name: "Route station BATTERY_BUFFER" }));
    fireEvent.pointerDown(screen.getByRole("button", { name: "Route station MARRIAGE_STATION" }));

    expect(screen.getByRole("status")).toHaveTextContent("BATTERY_DELIVERY updated");
    expect(screen.getAllByLabelText(/BATTERY_DELIVERY waypoint/)).toHaveLength(4);
  });

  it("adds and selects an alternative delivery route", () => {
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Add delivery route" }));

    expect(screen.getByRole("radio", { name: /BATTERY_DELIVERY_3/ })).toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent("BATTERY_DELIVERY_3 added");
  });

  it("draws a no-go zone on the map and persists it", async () => {
    api.createLayout.mockImplementation(savedLayout);
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Add no-go zone" }));
    expect(screen.getByRole("button", { name: "Create layout" })).toBeDisabled();

    const map = screen.getByRole("img", { name: "2D EV factory plant map" });
    Object.defineProperty(map, "getScreenCTM", {
      configurable: true,
      value: () => ({ inverse: () => ({}) }),
    });
    Object.defineProperty(map, "createSVGPoint", {
      configurable: true,
      value: () => {
        const point = {
          x: 0,
          y: 0,
          matrixTransform: () => ({ x: point.x, y: point.y }),
        };
        return point;
      },
    });
    const placePoint = (clientX: number, clientY: number) => {
      const event = new Event("pointerdown", { bubbles: true });
      Object.defineProperties(event, {
        button: { value: 0 },
        clientX: { value: clientX },
        clientY: { value: clientY },
      });
      fireEvent(map, event);
    };
    placePoint(10, 10);
    placePoint(20, 10);
    placePoint(20, 20);
    expect(screen.getByText(/3 placed/)).toBeInTheDocument();
    const finish = screen.getByRole("button", { name: "Finish zone" });
    expect(finish).toBeEnabled();
    fireEvent.click(finish);
    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    await waitFor(() => expect(api.createLayout).toHaveBeenCalledOnce());
    expect(api.createLayout.mock.calls[0]?.[0].content.no_go_zones).toEqual(
      expect.arrayContaining([expect.objectContaining({ id: "NO_GO_ZONE_1" })]),
    );
  });

  it("edits congestion delay without JSON", async () => {
    api.createLayout.mockImplementation(savedLayout);
    render(<LayoutsPage/>);

    fireEvent.change(screen.getByLabelText("Delay multiplier"), { target: { value: "1.5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    await waitFor(() => expect(api.createLayout).toHaveBeenCalledOnce());
    expect(api.createLayout.mock.calls[0]?.[0].content.congestion_zones[0]).toMatchObject({
      id: "WAREHOUSE_PRODUCTION_DOOR",
      delay_multiplier: 1.5,
    });
  });

  it("blocks saving when zone IDs are duplicated", () => {
    render(<LayoutsPage/>);
    const zoneIds = screen.getAllByLabelText("Zone ID");

    fireEvent.change(zoneIds[1]!, { target: { value: "GIGA_PRESS_CLEARANCE" } });

    expect(screen.getByRole("alert")).toHaveTextContent("Zone ID GIGA_PRESS_CLEARANCE is duplicated");
    expect(screen.getByRole("button", { name: "Create layout" })).toBeDisabled();
  });

  it("reports where the saved revision sits in candidate review", async () => {
    api.createLayout.mockImplementation(savedLayout);
    useFactoryStore.getState().setScenarios([{
      ...fixtureScenario,
      name: "battery-flow-v1",
      status: "SUBMITTED",
      config: { ...fixtureScenario.config, layout_id: "LAYOUT-0001", layout_version: 1 },
    }]);
    render(<LayoutsPage/>);

    expect(screen.queryByText(/is represented by candidate/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    expect(await screen.findByText("battery-flow-v1")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Candidate review progress" })).toBeInTheDocument();
  });

  it("says an unsimulated revision cannot be reviewed yet", async () => {
    api.createLayout.mockImplementation(savedLayout);
    render(<LayoutsPage/>);

    fireEvent.click(screen.getByRole("button", { name: "Create layout" }));

    expect(await screen.findByText(/has not been simulated yet/)).toBeInTheDocument();
  });

  it("blocks non-Designer roles", () => {
    state.role = "MONITOR";
    render(<LayoutsPage/>);
    expect(screen.getByText("Designer access required")).toBeInTheDocument();
    expect(screen.queryByText("Candidate geometry")).not.toBeInTheDocument();
  });
});
