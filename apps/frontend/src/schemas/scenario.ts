import { z } from "zod";

export const scenarioStatusSchema = z.enum([
  "DRAFT",
  "SIMULATED",
  "SUBMITTED",
  "APPROVED",
  "REJECTED",
  "APPLIED",
]);

export const scenarioConfigSchema = z.object({
  num_robots: z.number().int().min(1).max(10),
  num_tasks: z.number().int().min(1).max(10_000),
  task_arrival_interval: z.number().min(1).max(60),
  travel_time: z.number().positive().max(86_400),
  loading_time: z.number().positive().max(86_400),
  simulation_time: z.number().positive().max(86_400),
  layout_id: z.string().min(1).max(80).default("LAYOUT-DEFAULT"),
  layout_version: z.number().int().min(1).default(3),
  route_id: z.string().min(1).max(80).default("BATTERY_DELIVERY"),
  robot_speed_mps: z.number().positive().max(10).default(1),
  charger_count: z.number().int().min(1).max(20).default(1),
  route_distance_m: z.number().positive().max(100_000).default(30),
  congestion_multiplier: z.number().min(1).max(10).default(1),
});

export const scenarioRunRequestSchema = scenarioConfigSchema.extend({
  name: z.string().trim().min(1, "Name is required").max(80),
});

export const scenarioMetricsSchema = z.object({
  completed_tasks: z.number().int().nonnegative(),
  unfinished_tasks: z.number().int().nonnegative(),
  completion_rate: z.number().min(0).max(1),
  throughput_per_hour: z.number().nonnegative(),
  average_cycle_time: z.number().nonnegative(),
  average_waiting_time: z.number().nonnegative(),
  fleet_utilization_percent: z.number().min(0).max(100),
  starvation_events: z.number().int().nonnegative(),
  congestion_percent: z.number().min(0).max(100),
  travel_distance: z.number().nonnegative(),
  average_delivery_delay: z.number().nonnegative(),
});

const utcDateTimeSchema = z.string().datetime({ offset: true }).refine(
  (value) => value.endsWith("Z"),
  "Expected a UTC timestamp ending in Z",
);

export const scenarioSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  status: scenarioStatusSchema,
  config: scenarioConfigSchema,
  metrics: scenarioMetricsSchema,
  duration_ms: z.number().nonnegative(),
  created_at: utcDateTimeSchema,
  created_by: z.string().uuid().nullable(),
  reviewed_at: utcDateTimeSchema.nullable(),
  reviewed_by: z.string().uuid().nullable(),
  applied_at: utcDateTimeSchema.nullable(),
  applied_by: z.string().uuid().nullable(),
  version: z.number().int().min(1),
});

export type ScenarioStatus = z.infer<typeof scenarioStatusSchema>;
export type ScenarioConfig = z.infer<typeof scenarioConfigSchema>;
export type ScenarioRunRequest = z.input<typeof scenarioRunRequestSchema>;
export type ScenarioMetrics = z.infer<typeof scenarioMetricsSchema>;
export type Scenario = z.infer<typeof scenarioSchema>;
