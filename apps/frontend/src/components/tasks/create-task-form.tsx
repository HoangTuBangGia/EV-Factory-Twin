"use client";

import { type FormEvent, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { createTransportTaskRequestSchema } from "@/schemas/task";
import { useFactoryStore } from "@/stores/factory-store";

function message(error: unknown) {
  return error instanceof Error ? error.message : "Unable to create transport task.";
}

export function CreateTaskForm() {
  const updateCommand = useFactoryStore((state) => state.updateCommand);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitted(null);
    const data = new FormData(event.currentTarget);
    const parsed = createTransportTaskRequestSchema.safeParse({
      task_id: data.get("task_id"),
      payload_id: data.get("payload_id"),
      pickup_station_id: data.get("pickup_station_id"),
      dropoff_station_id: data.get("dropoff_station_id"),
      navigation_timeout_seconds: Number(data.get("navigation_timeout_seconds")),
      max_retries: Number(data.get("max_retries")),
    });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid task request.");
      return;
    }
    setBusy(true);
    try {
      const command = await apiClient.createTransportTask(parsed.data);
      updateCommand(command);
      setSubmitted(command.task_id);
      event.currentTarget.reset();
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel">
    <div className="panel-head">
      <div><h3>Create transport task</h3><span>Durable command to ROS Task Manager</span></div>
    </div>
    <form className="scenario-form" onSubmit={(event) => void submit(event)}>
      <div className="form-grid">
        <label>Task ID<input name="task_id" placeholder="TASK-LOCAL-0001" required/></label>
        <label>Payload ID<input name="payload_id" placeholder="BP-LOCAL-0001" required/></label>
        <label>Pickup station<select name="pickup_station_id" defaultValue="BATTERY_BUFFER">
          <option value="BATTERY_BUFFER">Battery Buffer</option>
          <option value="MARRIAGE_STATION">Marriage Station</option>
          <option value="CHARGING_STATION">Charging Station</option>
        </select></label>
        <label>Drop-off station<select name="dropoff_station_id" defaultValue="MARRIAGE_STATION">
          <option value="BATTERY_BUFFER">Battery Buffer</option>
          <option value="MARRIAGE_STATION">Marriage Station</option>
          <option value="CHARGING_STATION">Charging Station</option>
        </select></label>
        <label>Navigation timeout (s)<input name="navigation_timeout_seconds" type="number" min="1" max="300" defaultValue="30" required/></label>
        <label>Task retries<input name="max_retries" type="number" min="0" max="5" defaultValue="1" required/></label>
      </div>
      {error && <div className="scenario-error" role="alert">{error}</div>}
      {submitted && <p className="review-note" role="status">Task {submitted} queued for ROS delivery.</p>}
      <div className="button-row"><button className="button primary" type="submit" disabled={busy}>
        {busy ? "Queuing…" : "Create task"}
      </button></div>
    </form>
  </section>;
}
