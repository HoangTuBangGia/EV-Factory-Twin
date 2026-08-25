import { z } from "zod";

export const appRoleSchema = z.enum(["DESIGNER", "MONITOR"]);

export const currentUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string().min(1),
  role: appRoleSchema,
  is_active: z.boolean(),
});

export const loginResponseSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal("bearer"),
  expires_at: z.number().int().positive(),
  user: currentUserSchema,
});

export type AppRole = z.infer<typeof appRoleSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;
export type LoginResponse = z.infer<typeof loginResponseSchema>;
