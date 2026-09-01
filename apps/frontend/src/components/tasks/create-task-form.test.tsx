import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { factoryLayoutSchema, type FactoryLayout } from "@/schemas/factory";
import { fixtureApplyCommand } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { CreateTaskForm } from "./create-task-form";

vi.mock("@/lib/api-client", () => ({ apiClient: { createTransportTask: vi.fn() } }));
let appliedLayout: FactoryLayout = defaultFactoryLayout;
vi.mock("@/hooks/use-applied-factory-layout", () => ({
  useAppliedFactoryLayout: () => appliedLayout,
}));

describe("CreateTaskForm", () => {
  beforeEach(() => {
    useFactoryStore.getState().reset();
    appliedLayout = defaultFactoryLayout;
    vi.clearAllMocks();
  });

  it("queues a durable ROS transport-task command", async () => {
    const payload = {
      task_id: "TASK-LOCAL-0001",
      payload_id: "BP-LOCAL-0001",
      pickup_station_id: "BATTERY_BUFFER",
      dropoff_station_id: "MARRIAGE_STATION",
      navigation_timeout_seconds: 84,
      max_retries: 1,
    };
    const command = {
      ...fixtureApplyCommand,
      command_type: "CREATE_TRANSPORT_TASK" as const,
      scenario_id: null,
      task_id: payload.task_id,
      payload,
    };
    vi.mocked(apiClient.createTransportTask).mockResolvedValue(command);
    render(<CreateTaskForm/>);

    fireEvent.change(screen.getByLabelText("Task ID"), { target: { value: payload.task_id } });
    fireEvent.change(screen.getByLabelText("Payload ID"), { target: { value: payload.payload_id } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => expect(apiClient.createTransportTask).toHaveBeenCalledWith(payload));
    expect(await screen.findByRole("status")).toHaveTextContent(payload.task_id);
    expect(useFactoryStore.getState().commands[command.operation_id]).toEqual(command);
  });

  it("uses only the active delivery route and computes its safe timeout", () => {
    render(<CreateTaskForm/>);

    expect(screen.getByLabelText("Pickup station")).toHaveValue("BATTERY BUFFER");
    expect(screen.getByLabelText("Drop-off station")).toHaveValue("MARRIAGE STATION");
    expect(screen.getByLabelText("Navigation timeout (s)")).toHaveValue(84);
    expect(screen.getByText(/route BATTERY_DELIVERY · 1.2 m\/s/)).toBeInTheDocument();
  });

  it("honors an applied long route and excludes support-route stations", () => {
    appliedLayout = factoryLayoutSchema.parse({
      ...defaultFactoryLayout,
      active_route_id: "BATTERY_DELIVERY_LONG",
    });
    render(<CreateTaskForm/>);

    expect(screen.getByLabelText("Pickup station")).toHaveValue("BATTERY BUFFER");
    expect(screen.getByLabelText("Drop-off station")).toHaveValue("MARRIAGE STATION 2");
    expect(screen.getByLabelText("Navigation timeout (s)")).toHaveValue(119);
    expect(screen.queryByDisplayValue("CHARGING STATION")).not.toBeInTheDocument();
  });

  it("rejects a timeout below the applied route recommendation", async () => {
    render(<CreateTaskForm/>);
    fireEvent.change(screen.getByLabelText("Task ID"), { target: { value: "TASK-1" } });
    fireEvent.change(screen.getByLabelText("Payload ID"), { target: { value: "BP-1" } });
    fireEvent.change(screen.getByLabelText("Navigation timeout (s)"), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Navigation timeout must be at least 84 seconds",
    );
    expect(apiClient.createTransportTask).not.toHaveBeenCalled();
  });
});
