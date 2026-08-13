import { z } from "zod";

export const scenarioStatusSchema = z.enum([
  "DRAFT",
  "SIMULATED",
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
});

export const scenarioSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  status: scenarioStatusSchema,
  config: scenarioConfigSchema,
  metrics: scenarioMetricsSchema,
  duration_ms: z.number().nonnegative(),
  reviewed_at: z.string().datetime().nullable().optional(),
  applied_at: z.string().datetime().nullable().optional(),
});

export type ScenarioStatus = z.infer<typeof scenarioStatusSchema>;
export type ScenarioConfig = z.infer<typeof scenarioConfigSchema>;
export type ScenarioRunRequest = z.infer<typeof scenarioRunRequestSchema>;
export type ScenarioMetrics = z.infer<typeof scenarioMetricsSchema>;
export type Scenario = z.infer<typeof scenarioSchema>;
