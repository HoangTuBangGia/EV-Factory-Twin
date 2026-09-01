import { z } from "zod";

export const alertSeveritySchema = z.enum(["INFO", "WARNING", "CRITICAL"]);
export const alertCodeSchema = z.enum([
  "LOW_BATTERY",
  "ROBOT_WAITING",
  "TASK_BACKLOG",
  "STARVATION",
  "ROBOT_ERROR",
  "STALE_TELEMETRY",
  "BRIDGE_DISCONNECTED",
  "COMMAND_TIMEOUT",
  "CONGESTION",
  "COLLISION",
]);
export const factoryAlertSchema = z.object({
  id: z.string().uuid(),
  dedupe_key: z.string().min(1).max(200),
  severity: alertSeveritySchema,
  code: alertCodeSchema,
  status: z.enum(["ACTIVE", "CLEARED"]),
  message: z.string().min(1).max(1_000),
  robot_id: z.string().nullable(),
  task_id: z.string().nullable(),
  operation_id: z.string().uuid().nullable(),
  timestamp: z.string().datetime({ offset: true }),
  last_seen_at: z.string().datetime({ offset: true }),
  cleared_at: z.string().datetime({ offset: true }).nullable(),
  acknowledged_at: z.string().datetime({ offset: true }).nullable(),
  acknowledged_by: z.string().uuid().nullable(),
});

export type FactoryAlert = z.infer<typeof factoryAlertSchema>;
