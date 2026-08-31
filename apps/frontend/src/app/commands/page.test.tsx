import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { useFactoryStore } from "@/stores/factory-store";
import CommandsPage from "./page";

const auth = vi.hoisted(() => ({ role: "MONITOR" as "DESIGNER" | "MONITOR" }));
const api = vi.hoisted(() => ({ getCommands: vi.fn(), retryCommand: vi.fn() }));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: auth.role } }),
}));
vi.mock("@/lib/api-client", () => ({ apiClient: api }));

const command = {
  operation_id: "33333333-3333-4333-8333-333333333333",
  command_type: "APPLY_SCENARIO" as const,
  scenario_id: "SCN-0001",
  task_id: null,
  status: "TIMED_OUT" as const,
  payload: {
    num_robots: 2, num_tasks: 10, task_arrival_interval: 5, travel_time: 30,
    loading_time: 5, simulation_time: 600, layout_id: "LAYOUT-DEFAULT",
    layout_version: 1, route_id: "BATTERY_DELIVERY", robot_speed_mps: 1,
    charger_count: 1, route_distance_m: 30, congestion_multiplier: 1,
  },
  timeout_seconds: 30,
  max_retries: 1,
  attempts: [{
    attempt_number: 1, status: "TIMED_OUT" as const, leased_by: "edge-main",
    lease_expires_at: "2026-08-24T00:00:30Z", acknowledged_at: null,
    completed_at: "2026-08-24T00:00:30Z", detail: "command attempt timed out",
  }],
  requested_by: "22222222-2222-4222-8222-222222222222",
  created_at: "2026-08-24T00:00:00Z",
  updated_at: "2026-08-24T00:00:30Z",
};

beforeEach(() => {
  auth.role = "MONITOR";
  useFactoryStore.getState().reset();
  api.getCommands.mockResolvedValue([command]);
  api.retryCommand.mockResolvedValue({
    ...command,
    status: "PENDING",
    attempts: [
      ...command.attempts,
      { attempt_number: 2, status: "PENDING", leased_by: null, lease_expires_at: null,
        acknowledged_at: null, completed_at: null, detail: "" },
    ],
  });
  vi.clearAllMocks();
});

it("shows durable attempts and lets Monitor retry within budget", async () => {
  render(<CommandsPage/>);

  expect(await screen.findByText("command attempt timed out")).toBeInTheDocument();
  expect(screen.getByText("0/1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry command" }));

  await waitFor(() => expect(api.retryCommand).toHaveBeenCalledWith(command.operation_id));
  expect(await screen.findAllByText("PENDING")).toHaveLength(2);
  expect(screen.getByText("1/1")).toBeInTheDocument();
});

it("keeps command history read-only for Designer", async () => {
  auth.role = "DESIGNER";
  render(<CommandsPage/>);

  expect(await screen.findByText("command attempt timed out")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry command" })).not.toBeInTheDocument();
});
