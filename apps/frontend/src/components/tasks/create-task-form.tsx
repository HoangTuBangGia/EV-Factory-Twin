"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useAppliedFactoryLayout } from "@/hooks/use-applied-factory-layout";
import { apiClient } from "@/lib/api-client";
import type { FactoryLayout, FactoryStation } from "@/schemas/factory";
import { createTransportTaskRequestSchema } from "@/schemas/task";
import { useFactoryStore } from "@/stores/factory-store";

const MIN_NAVIGATION_TIMEOUT_SECONDS = 30;
const MAX_NAVIGATION_TIMEOUT_SECONDS = 300;
const ROUTE_TIME_SAFETY_FACTOR = 1.5;
const TASK_HANDLING_ALLOWANCE_SECONDS = 30;

function message(error: unknown) {
  return error instanceof Error ? error.message : "Unable to create transport task.";
}

function activeRoute(layout: FactoryLayout) {
  return layout.routes.find((route) => (
    route.id === layout.active_route_id && route.kind === "DELIVERY"
  ));
}

export function recommendedNavigationTimeout(layout: FactoryLayout) {
  const route = activeRoute(layout);
  const distance = route?.waypoints.slice(1).reduce((total, point, index) => {
    const previous = route.waypoints[index];
    return total + Math.hypot(point.x - previous.x, point.y - previous.y);
  }, 0) ?? 0;
  const travelSeconds = distance / layout.config.robot_speed_mps;
  return Math.max(
    MIN_NAVIGATION_TIMEOUT_SECONDS,
    Math.ceil(travelSeconds * ROUTE_TIME_SAFETY_FACTOR + TASK_HANDLING_ALLOWANCE_SECONDS),
  );
}

function stationLabel(station: FactoryStation) {
  return station.id.replaceAll("_", " ");
}

export function CreateTaskForm() {
  const layout = useAppliedFactoryLayout();
  const route = activeRoute(layout);
  const pickup = layout.stations.find((station) => station.id === route?.start_station_id);
  const dropoff = layout.stations.find((station) => station.id === route?.end_station_id);
  const updateCommand = useFactoryStore((state) => state.updateCommand);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const recommendedTimeout = recommendedNavigationTimeout(layout);
  const [navigationTimeout, setNavigationTimeout] = useState(
    Math.min(recommendedTimeout, MAX_NAVIGATION_TIMEOUT_SECONDS),
  );
  useEffect(() => {
    setNavigationTimeout(Math.min(recommendedTimeout, MAX_NAVIGATION_TIMEOUT_SECONDS));
  }, [recommendedTimeout]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitted(null);
    const data = new FormData(event.currentTarget);
    if (recommendedTimeout > MAX_NAVIGATION_TIMEOUT_SECONDS) {
      setError("This route exceeds the supported 300-second navigation timeout.");
      return;
    }
    if (Number(data.get("navigation_timeout_seconds")) < recommendedTimeout) {
      setError(
        `Navigation timeout must be at least ${recommendedTimeout} seconds for the applied layout route.`,
      );
      return;
    }
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
        <label>Pickup station<input value={pickup ? stationLabel(pickup) : "Unavailable"} readOnly/></label>
        <input name="pickup_station_id" value={pickup?.id ?? ""} type="hidden"/>
        <label>Drop-off station<input value={dropoff ? stationLabel(dropoff) : "Unavailable"} readOnly/></label>
        <input name="dropoff_station_id" value={dropoff?.id ?? ""} type="hidden"/>
        <label>Navigation timeout (s)<input
          name="navigation_timeout_seconds" type="number"
          min="1" max={MAX_NAVIGATION_TIMEOUT_SECONDS}
          value={navigationTimeout}
          onChange={(event) => setNavigationTimeout(Number(event.target.value))}
          required
        /></label>
        <label>Task retries<input name="max_retries" type="number" min="0" max="5" defaultValue="1" required/></label>
      </div>
      <p className="form-help">
        Applied layout {layout.id} · v{layout.version} · route {layout.active_route_id}
        {" · "}{layout.config.robot_speed_mps} m/s.
        Timeout includes route travel margin and task handling time.
      </p>
      {error && <div className="scenario-error" role="alert">{error}</div>}
      {submitted && <p className="review-note" role="status">Task {submitted} queued for ROS delivery.</p>}
      <div className="button-row"><button
        className="button primary" type="submit"
        disabled={busy || !route || !pickup || !dropoff
          || recommendedTimeout > MAX_NAVIGATION_TIMEOUT_SECONDS}
      >
        {busy ? "Queuing…" : "Create task"}
      </button></div>
    </form>
  </section>;
}
