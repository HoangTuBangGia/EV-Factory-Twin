import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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

describe("LayoutsPage", () => {
  beforeEach(() => {
    state.role = "DESIGNER";
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
    api.createLayout.mockImplementation(async (request) => ({
      ...request.content,
      layout_id: "LAYOUT-0001",
      name: request.name,
      version: 1,
      created_by: "11111111-1111-4111-8111-111111111111",
      created_at: "2026-08-24T00:00:00Z",
      archived_at: null,
    }));
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

  it("blocks non-Designer roles", () => {
    state.role = "MONITOR";
    render(<LayoutsPage/>);
    expect(screen.getByText("Designer access required")).toBeInTheDocument();
    expect(screen.queryByText("Candidate geometry")).not.toBeInTheDocument();
  });
});
