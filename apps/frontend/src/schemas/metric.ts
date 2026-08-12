import { z } from "zod";

export const factoryMetricsSchema = z.object({
  completed_tasks: z.number(),
  throughput_per_hour: z.number(),
  average_cycle_time_seconds: z.number(),
  active_tasks: z.number(),
  queued_tasks: z.number(),
  starvation_events: z.number(),
  fleet_utilization_percent: z.number(),
});

export type FactoryMetrics = z.infer<typeof factoryMetricsSchema>;
