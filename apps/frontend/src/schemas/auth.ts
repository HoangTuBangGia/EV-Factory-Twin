import { z } from "zod";

export const appRoleSchema = z.enum(["DESIGNER", "MONITOR"]);

export const currentUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string().min(1),
  role: appRoleSchema,
  is_active: z.boolean(),
});

export type AppRole = z.infer<typeof appRoleSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;
