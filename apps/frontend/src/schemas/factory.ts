import { z } from "zod";

export const mockFactoryConfigSchema = z.object({
  robot_count: z.number().int().min(1).max(10),
  task_interval_seconds: z.number().min(1).max(60),
  robot_speed_mps: z.number().min(0.1).max(3),
  simulation_speed: z.number().min(0.25).max(10),
  low_battery_threshold: z.number().min(0).max(100),
});

export type MockFactoryConfig = z.infer<typeof mockFactoryConfigSchema>;
