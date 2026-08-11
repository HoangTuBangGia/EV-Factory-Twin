import type { FactoryAlert } from "@/schemas/alert";
import type { FactoryMetrics } from "@/schemas/metric";
import type { Robot } from "@/schemas/robot";
import type { Task } from "@/schemas/task";

const now = "2026-08-11T04:00:00.000Z";

export const fixtureRobots: Robot[] = [
  { id: "AMR-01", name: "Atlas 01", status: "DELIVERING", battery: 82, pose: { x: 11.5, y: 9.2, yaw: 0 }, velocity: { linear: 1.1, angular: 0 }, task_id: "TASK-101", payload_id: "BP-101", last_seen_at: now },
  { id: "AMR-02", name: "Atlas 02", status: "MOVING_TO_PICKUP", battery: 64, pose: { x: 6.2, y: 11.4, yaw: -0.4 }, velocity: { linear: 0.9, angular: 0.1 }, task_id: "TASK-102", payload_id: null, last_seen_at: now },
  { id: "AMR-03", name: "Atlas 03", status: "IDLE", battery: 96, pose: { x: 9.1, y: 4.5, yaw: 1.57 }, velocity: { linear: 0, angular: 0 }, task_id: null, payload_id: null, last_seen_at: now },
  { id: "AMR-04", name: "Atlas 04", status: "PICKING", battery: 47, pose: { x: 3.2, y: 10.5, yaw: 0 }, velocity: { linear: 0, angular: 0 }, task_id: "TASK-103", payload_id: "BP-103", last_seen_at: now },
  { id: "AMR-05", name: "Atlas 05", status: "CHARGING", battery: 16, pose: { x: 3.1, y: 2.1, yaw: 3.14 }, velocity: { linear: 0, angular: 0 }, task_id: null, payload_id: null, last_seen_at: now },
];

export const fixtureTasks: Task[] = [
  { task_id: "TASK-101", type: "DELIVER_BATTERY", payload_id: "BP-101", pickup: "Battery Buffer", dropoff: "Marriage Station", assigned_robot_id: "AMR-01", status: "IN_PROGRESS", created_at: now, started_at: now, completed_at: null },
  { task_id: "TASK-102", type: "DELIVER_BATTERY", payload_id: "BP-102", pickup: "Battery Buffer", dropoff: "Marriage Station", assigned_robot_id: "AMR-02", status: "ASSIGNED", created_at: now, started_at: null, completed_at: null },
  { task_id: "TASK-103", type: "DELIVER_BATTERY", payload_id: "BP-103", pickup: "Battery Buffer", dropoff: "Marriage Station", assigned_robot_id: "AMR-04", status: "PICKUP", created_at: now, started_at: now, completed_at: null },
];

export const fixtureMetrics: FactoryMetrics = {
  completed_tasks: 184, throughput_per_hour: 61.4, average_cycle_time_seconds: 52.8,
  active_tasks: 3, queued_tasks: 1, starvation_events: 2, fleet_utilization_percent: 72.1,
};

export const fixtureAlerts: FactoryAlert[] = [
  { id: "ALT-001", severity: "WARNING", code: "LOW_BATTERY", message: "AMR-05 battery below 20%", robot_id: "AMR-05", task_id: null, timestamp: now },
  { id: "ALT-002", severity: "INFO", code: "TASK_ASSIGNED", message: "TASK-102 assigned to AMR-02", robot_id: "AMR-02", task_id: "TASK-102", timestamp: now },
  { id: "ALT-003", severity: "CRITICAL", code: "STARVATION_RISK", message: "Marriage Station supply risk detected", robot_id: null, task_id: null, timestamp: now },
];

export const throughputHistory = [42, 48, 46, 55, 58, 61.4];
export const cycleHistory = [68, 64, 62, 58, 55, 52.8];
