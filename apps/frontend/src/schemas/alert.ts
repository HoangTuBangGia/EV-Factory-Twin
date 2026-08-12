import { z } from "zod";

export const alertSeveritySchema = z.enum(["INFO", "WARNING", "CRITICAL"]);
export const factoryAlertSchema = z.object({
  id: z.string(), severity: alertSeveritySchema, code: z.string(), message: z.string(),
  robot_id: z.string().nullable(), task_id: z.string().nullable(), timestamp: z.string(),
});

export type FactoryAlert = z.infer<typeof factoryAlertSchema>;
