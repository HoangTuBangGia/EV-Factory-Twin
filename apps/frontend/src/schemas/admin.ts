import { z } from "zod";
import { appRoleSchema } from "@/schemas/auth";

export const adminUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string().min(1),
  role: appRoleSchema,
  is_active: z.boolean(),
  created_at: z.string().datetime(),
});

export const adminUserUpdateSchema = z.object({
  role: appRoleSchema.optional(),
  is_active: z.boolean().optional(),
}).refine((update) => update.role !== undefined || update.is_active !== undefined, {
  message: "At least one user field must be updated",
});

export const adminInviteRequestSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  display_name: z.string().trim().min(1, "Display name is required").max(120),
  role: appRoleSchema,
});

export const auditActionSchema = z.enum([
  "SCENARIO_RUN",
  "SCENARIO_APPROVED",
  "SCENARIO_REJECTED",
  "SCENARIO_APPLIED",
  "FACTORY_RESET",
  "ROLE_CHANGED",
  "USER_DISABLED",
  "USER_ENABLED",
  "USER_INVITED",
]);

export const auditEventSchema = z.object({
  id: z.number().int().positive(),
  actor_id: z.string().uuid(),
  actor_role: appRoleSchema,
  action: auditActionSchema,
  resource_type: z.string().min(1),
  resource_id: z.string().min(1),
  before_data: z.record(z.string(), z.unknown()).nullable(),
  after_data: z.record(z.string(), z.unknown()).nullable(),
  request_id: z.string().uuid(),
  created_at: z.string().datetime(),
});

export type AdminUser = z.infer<typeof adminUserSchema>;
export type AdminUserUpdate = z.infer<typeof adminUserUpdateSchema>;
export type AdminInviteRequest = z.infer<typeof adminInviteRequestSchema>;
export type AuditAction = z.infer<typeof auditActionSchema>;
export type AuditEvent = z.infer<typeof auditEventSchema>;
