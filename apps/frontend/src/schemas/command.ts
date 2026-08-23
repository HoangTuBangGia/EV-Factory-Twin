import { z } from "zod";
import { scenarioConfigSchema } from "./scenario";

export const commandStatusSchema = z.enum([
  "PENDING",
  "ACKNOWLEDGED",
  "COMPLETED",
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

export const commandSchema = z.object({
  operation_id: z.string().uuid(),
  scenario_id: z.string().min(1),
  status: commandStatusSchema,
  payload: scenarioConfigSchema,
  timeout_seconds: z.number().positive().max(300),
  max_retries: z.number().int().min(0).max(5),
  attempts: z.array(commandAttemptSchema).min(1),
  requested_by: z.string().uuid(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});

export const applyScenarioRequestSchema = z.object({
  timeout_seconds: z.number().positive().max(300).default(30),
  max_retries: z.number().int().min(0).max(5).default(1),
});

export type Command = z.infer<typeof commandSchema>;
export type ApplyScenarioRequest = z.input<typeof applyScenarioRequestSchema>;
