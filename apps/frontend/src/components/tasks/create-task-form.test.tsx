import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import { fixtureApplyCommand } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { CreateTaskForm } from "./create-task-form";

vi.mock("@/lib/api-client", () => ({ apiClient: { createTransportTask: vi.fn() } }));

describe("CreateTaskForm", () => {
  beforeEach(() => {
    useFactoryStore.getState().reset();
    vi.clearAllMocks();
  });

  it("queues a durable ROS transport-task command", async () => {
    const payload = {
      task_id: "TASK-LOCAL-0001",
      payload_id: "BP-LOCAL-0001",
      pickup_station_id: "BATTERY_BUFFER",
      dropoff_station_id: "MARRIAGE_STATION",
      navigation_timeout_seconds: 30,
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

  it("rejects identical pickup and drop-off stations before calling the API", async () => {
    render(<CreateTaskForm/>);
    fireEvent.change(screen.getByLabelText("Task ID"), { target: { value: "TASK-1" } });
    fireEvent.change(screen.getByLabelText("Payload ID"), { target: { value: "BP-1" } });
    fireEvent.change(screen.getByLabelText("Drop-off station"), { target: { value: "BATTERY_BUFFER" } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Pickup and drop-off stations must differ");
    expect(apiClient.createTransportTask).not.toHaveBeenCalled();
  });
});
