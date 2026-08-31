import type { AppRole } from "@/schemas/auth";

export const permissions = [
  "operations:view",
  "scenarios:view",
  "scenarios:run",
  "scenarios:review",
  "scenarios:apply",
  "factory:control",
  "layout:view",
  "layout:edit",
  "commands:view",
  "commands:retry",
] as const;

export type Permission = (typeof permissions)[number];

/**
 * `layout:view` is read-only geometry inspection, which the Backend already
 * grants to both roles; only authoring geometry stays Designer-only.
 */
export const rolePermissions: Readonly<Record<AppRole, readonly Permission[]>> = {
  DESIGNER: [
    "operations:view",
    "scenarios:view",
    "scenarios:run",
    "layout:view",
    "layout:edit",
    "commands:view",
  ],
  MONITOR: [
    "operations:view",
    "scenarios:view",
    "scenarios:review",
    "scenarios:apply",
    "factory:control",
    "layout:view",
    "commands:view",
    "commands:retry",
  ],
};

export function can(role: AppRole | null | undefined, permission: Permission) {
  return role ? rolePermissions[role].includes(permission) : false;
}
