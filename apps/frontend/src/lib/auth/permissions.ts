import type { AppRole } from "@/schemas/auth";

export const permissions = [
  "operations:view",
  "scenarios:view",
  "scenarios:run",
  "scenarios:review",
  "scenarios:apply",
  "factory:control",
  "layout:edit",
] as const;

export type Permission = (typeof permissions)[number];

export const rolePermissions: Readonly<Record<AppRole, readonly Permission[]>> = {
  DESIGNER: [
    "operations:view",
    "scenarios:view",
    "scenarios:run",
    "layout:edit",
  ],
  MONITOR: [
    "operations:view",
    "scenarios:view",
    "scenarios:review",
    "scenarios:apply",
    "factory:control",
  ],
};

export function can(role: AppRole | null | undefined, permission: Permission) {
  return role ? rolePermissions[role].includes(permission) : false;
}
