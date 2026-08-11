import { z } from "zod";

export const robotStatusSchema = z.enum([
  "IDLE", "MOVING_TO_PICKUP", "PICKING", "DELIVERING", "DROPPING",
  "WAITING", "CHARGING", "ERROR", "OFFLINE",
]);

export const poseSchema = z.object({ x: z.number(), y: z.number(), yaw: z.number() });
export const velocitySchema = z.object({ linear: z.number(), angular: z.number() });

export const robotSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: robotStatusSchema,
  battery: z.number().min(0).max(100),
  pose: poseSchema,
  velocity: velocitySchema,
  task_id: z.string().nullable(),
  payload_id: z.string().nullable(),
  last_seen_at: z.string(),
});

export const robotTelemetrySchema = z.object({
  timestamp: z.string(),
  robot_id: z.string(),
  pose: poseSchema,
  velocity: velocitySchema,
  battery: z.number().min(0).max(100),
  status: robotStatusSchema,
  task_id: z.string().nullable(),
  payload_id: z.string().nullable(),
});

export type RobotStatus = z.infer<typeof robotStatusSchema>;
export type Robot = z.infer<typeof robotSchema>;
export type RobotTelemetry = z.infer<typeof robotTelemetrySchema>;
