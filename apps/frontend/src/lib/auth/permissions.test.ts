import { describe, expect, it } from "vitest";
import type { AppRole } from "@/schemas/auth";
import { can, permissions, rolePermissions } from "./permissions";

describe("role permission matrix", () => {
  it.each(Object.keys(rolePermissions) as AppRole[])(
    "%s only receives its declared permissions",
    (role) => {
      expect(permissions.filter((permission) => can(role, permission))).toEqual(rolePermissions[role]);
    },
  );

  it("keeps operational approval separate from scenario creation", () => {
    expect(can("DESIGNER", "scenarios:run")).toBe(true);
    expect(can("DESIGNER", "scenarios:review")).toBe(false);
    expect(can("DESIGNER", "scenarios:apply")).toBe(false);
    expect(can("MONITOR", "scenarios:run")).toBe(false);
    expect(can("MONITOR", "scenarios:review")).toBe(true);
    expect(can("MONITOR", "scenarios:apply")).toBe(true);
  });

  it("allows both roles to inspect commands but only Monitor to retry", () => {
    expect(can("DESIGNER", "commands:view")).toBe(true);
    expect(can("DESIGNER", "commands:retry")).toBe(false);
    expect(can("MONITOR", "commands:view")).toBe(true);
    expect(can("MONITOR", "commands:retry")).toBe(true);
  });

  it("lets both roles read geometry while only Designer authors it", () => {
    expect(can("DESIGNER", "layout:view")).toBe(true);
    expect(can("DESIGNER", "layout:edit")).toBe(true);
    expect(can("MONITOR", "layout:view")).toBe(true);
    expect(can("MONITOR", "layout:edit")).toBe(false);
  });

  it("denies every permission when no role is available", () => {
    expect(permissions.every((permission) => !can(null, permission))).toBe(true);
  });
});
