import { z } from "zod";
import { scenarioConfigSchema } from "./scenario";
import { createTransportTaskRequestSchema } from "./task";

export const commandStatusSchema = z.enum([
  "PENDING",
  "ACKNOWLEDGED",
  "COMPLETED",
  "REQUIRES_RELAUNCH",
  "FAILED",
  "TIMED_OUT",
]);

export const commandAttemptSchema = z.object({
  attempt_number: z.number().int().min(1),
  status: commandStatusSchema,
  leased_by: z.string().nullable(),
  lease_expires_at: z.string().datetime({ offset: true }).nullable(),
  acknowledged_at: z.string().datetime({ offset: true }).nullable(),
  completed_at: z.string().datetime({ offset: true }).nullable(),
  detail: z.string(),
});

const commandBaseSchema = z.object({
  operation_id: z.string().uuid(),
  status: commandStatusSchema,
  timeout_seconds: z.number().positive().max(300),
  max_retries: z.number().int().min(0).max(5),
  attempts: z.array(commandAttemptSchema).min(1),
  requested_by: z.string().uuid(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});

export const commandSchema = z.discriminatedUnion("command_type", [
  commandBaseSchema.extend({
    command_type: z.literal("APPLY_SCENARIO"),
    scenario_id: z.string().min(1),
    task_id: z.null(),
    payload: scenarioConfigSchema,
  }),
  commandBaseSchema.extend({
    command_type: z.literal("CREATE_TRANSPORT_TASK"),
    scenario_id: z.null(),
    task_id: z.string().min(1),
    payload: createTransportTaskRequestSchema,
  }),
]);

export const applyScenarioRequestSchema = z.object({
  timeout_seconds: z.number().positive().max(300).default(30),
  max_retries: z.number().int().min(0).max(5).default(1),
});

export const scenarioCompatibilitySchema = z.object({
  status: z.enum(["LIVE_APPLY", "REQUIRES_RELAUNCH", "RUNTIME_UNAVAILABLE"]),
  details: z.array(z.string()),
  dynamic_updates: z.array(z.string()),
});

export type Command = z.infer<typeof commandSchema>;
export type ApplyScenarioRequest = z.input<typeof applyScenarioRequestSchema>;
export type ScenarioCompatibility = z.infer<typeof scenarioCompatibilitySchema>;
