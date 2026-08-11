import { z } from "zod";
import { factoryAlertSchema } from "./alert";
import { factoryMetricsSchema } from "./metric";
import { robotTelemetrySchema } from "./robot";
import { taskSchema } from "./task";

export const factoryEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("robot.telemetry"), data: robotTelemetrySchema }),
  z.object({ type: z.literal("task.updated"), data: taskSchema }),
  z.object({ type: z.literal("metrics.updated"), data: factoryMetricsSchema }),
  z.object({ type: z.literal("alert.created"), data: factoryAlertSchema }),
]);

export type FactoryEvent = z.infer<typeof factoryEventSchema>;
