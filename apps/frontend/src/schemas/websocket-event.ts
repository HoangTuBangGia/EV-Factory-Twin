import { z } from "zod";
import { factoryAlertSchema } from "./alert";
import { appRoleSchema } from "./auth";
import { commandSchema } from "./command";
import { factoryMetricsSchema } from "./metric";
import { robotTelemetrySchema } from "./robot";
import { taskSchema } from "./task";

export const factoryEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("robot.telemetry"), data: robotTelemetrySchema }),
  z.object({ type: z.literal("task.updated"), data: taskSchema }),
  z.object({ type: z.literal("metrics.updated"), data: factoryMetricsSchema }),
  z.object({ type: z.literal("alert.created"), data: factoryAlertSchema }),
  z.object({ type: z.literal("alert.updated"), data: factoryAlertSchema }),
  z.object({ type: z.literal("factory.reset"), data: z.null() }),
  z.object({ type: z.literal("command.updated"), data: commandSchema }),
]);

export const factorySocketAuthRequestSchema = z.object({
  type: z.literal("auth"),
  access_token: z.string().min(1),
});

export const factorySocketAuthOkSchema = z.object({
  type: z.literal("auth.ok"),
  data: z.object({
    user_id: z.string().uuid(),
    display_name: z.string().min(1),
    role: appRoleSchema,
    expires_at: z.number().int().positive(),
  }),
});

export type FactoryEvent = z.infer<typeof factoryEventSchema>;
export type FactorySocketAuthOk = z.infer<typeof factorySocketAuthOkSchema>;
