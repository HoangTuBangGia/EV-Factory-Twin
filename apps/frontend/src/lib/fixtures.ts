import type { FactoryAlert } from "@/schemas/alert";
import type { Command } from "@/schemas/command";
import type { LayoutVersion } from "@/schemas/layout";
import type { FactoryMetrics } from "@/schemas/metric";
import type { Robot } from "@/schemas/robot";
import type { Scenario } from "@/schemas/scenario";
import type { Task } from "@/schemas/task";

const now = "2026-08-11T04:00:00.000Z";

export const fixtureRobots: Robot[] = [
  { id: "AMR-01", name: "Atlas 01", status: "DELIVERING", battery: 82, pose: { x: 40, y: 20, yaw: 0 }, velocity: { linear: 1.1, angular: 0 }, task_id: "TASK-101", payload_id: "BP-101", last_seen_at: now },
  { id: "AMR-02", name: "Atlas 02", status: "MOVING_TO_PICKUP", battery: 64, pose: { x: 32, y: 24, yaw: -1.57 }, velocity: { linear: 0.9, angular: 0.1 }, task_id: "TASK-102", payload_id: null, last_seen_at: now },
  { id: "AMR-03", name: "Atlas 03", status: "IDLE", battery: 96, pose: { x: 30.8, y: 13, yaw: 0 }, velocity: { linear: 0, angular: 0 }, task_id: null, payload_id: null, last_seen_at: now },
  { id: "AMR-04", name: "Atlas 04", status: "PICKING", battery: 47, pose: { x: 32, y: 29, yaw: 0 }, velocity: { linear: 0, angular: 0 }, task_id: "TASK-103", payload_id: "BP-103", last_seen_at: now },
  { id: "AMR-05", name: "Atlas 05", status: "CHARGING", battery: 16, pose: { x: 32, y: 11, yaw: 3.14 }, velocity: { linear: 0, angular: 0 }, task_id: null, payload_id: null, last_seen_at: now },
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
  { id: "11111111-1111-4111-8111-111111111111", dedupe_key: "LOW_BATTERY:AMR-05", severity: "WARNING", code: "LOW_BATTERY", status: "ACTIVE", message: "AMR-05 battery below 20%", robot_id: "AMR-05", task_id: null, operation_id: null, timestamp: now, last_seen_at: now, cleared_at: null },
  { id: "22222222-2222-4222-8222-222222222222", dedupe_key: "TASK_BACKLOG", severity: "INFO", code: "TASK_BACKLOG", status: "ACTIVE", message: "Battery task backlog detected", robot_id: null, task_id: "TASK-102", operation_id: null, timestamp: now, last_seen_at: now, cleared_at: null },
  { id: "33333333-3333-4333-8333-333333333333", dedupe_key: "STARVATION", severity: "CRITICAL", code: "STARVATION", status: "ACTIVE", message: "Marriage Station supply risk detected", robot_id: null, task_id: null, operation_id: null, timestamp: now, last_seen_at: now, cleared_at: null },
];

export const throughputHistory = [42, 48, 46, 55, 58, 61.4];
export const cycleHistory = [68, 64, 62, 58, 55, 52.8];

export const fixtureScenarioConfig: Scenario["config"] = {
  num_robots: 5, num_tasks: 500, task_arrival_interval: 5, travel_time: 30, loading_time: 10,
  simulation_time: 3600, layout_id: "LAYOUT-DEFAULT", layout_version: 1,
  route_id: "BATTERY_DELIVERY", robot_speed_mps: 1, charger_count: 1, route_distance_m: 30,
  congestion_multiplier: 1,
};

export const fixtureScenario: Scenario = {
  id: "SCN-0001", name: "candidate-01", status: "SIMULATED", config: fixtureScenarioConfig,
  metrics: {
    completed_tasks: 355, unfinished_tasks: 145, completion_rate: 0.71, throughput_per_hour: 355,
    average_cycle_time: 900, average_waiting_time: 850, fleet_utilization_percent: 72,
    starvation_events: 3, congestion_percent: 11, travel_distance: 12_400,
    average_delivery_delay: 8,
  },
  duration_ms: 2.4, created_at: "2026-08-14T00:00:00.000Z",
  created_by: "11111111-1111-4111-8111-111111111111",
  reviewed_at: null, reviewed_by: null, applied_at: null, applied_by: null, version: 1,
};

export const fixtureLayoutVersion: LayoutVersion = {
  layout_id: "LAYOUT-DEFAULT", name: "Battery logistics baseline", version: 1,
  width: 120, height: 40,
  stations: [
    { id: "BATTERY_BUFFER", type: "BATTERY_BUFFER", x: 30, y: 20 },
    { id: "MARRIAGE_STATION", type: "MARRIAGE_STATION", x: 60, y: 20 },
    { id: "CHARGING_STATION", type: "CHARGING_STATION", x: 30, y: 10 },
  ],
  routes: [{
    id: "BATTERY_DELIVERY", kind: "DELIVERY",
    start_station_id: "BATTERY_BUFFER", end_station_id: "MARRIAGE_STATION",
    waypoints: [{ x: 30, y: 20 }, { x: 60, y: 20 }],
  }],
  no_go_zones: [],
  congestion_zones: [{
    id: "WAREHOUSE_PRODUCTION_DOOR", delay_multiplier: 1.25,
    points: [{ x: 38, y: 17.5 }, { x: 42, y: 17.5 }, { x: 42, y: 22.5 }],
  }],
  config: {
    robot_count: 5, demand_interval_seconds: 8, robot_speed_mps: 1.2, charger_count: 2,
  },
  created_by: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-08-11T00:00:00.000Z", archived_at: null,
};

export const fixtureApplyCommand = {
  operation_id: "33333333-3333-4333-8333-333333333333",
  command_type: "APPLY_SCENARIO", scenario_id: fixtureScenario.id, task_id: null,
  status: "PENDING", payload: fixtureScenarioConfig, timeout_seconds: 30, max_retries: 1,
  attempts: [{
    attempt_number: 1, status: "PENDING", leased_by: null, lease_expires_at: null,
    acknowledged_at: null, completed_at: null, detail: "",
  }],
  requested_by: "22222222-2222-4222-8222-222222222222",
  created_at: "2026-08-14T00:10:00.000Z", updated_at: "2026-08-14T00:10:00.000Z",
} satisfies Command;
