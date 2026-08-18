import { describe, expect, it } from "vitest";
import { defaultRouteForRole, safeReturnTo } from "./return-to";

describe("safeReturnTo", () => {
  it("keeps an internal route including its query", () => {
    expect(safeReturnTo("/scenarios?status=SIMULATED")).toBe("/scenarios?status=SIMULATED");
  });

  it.each([
    "https://attacker.example/path",
    "//attacker.example/path",
    "/\\attacker.example/path",
    "/login",
  ])("rejects unsafe destination %s", (destination) => {
    expect(safeReturnTo(destination, "/factory")).toBe("/factory");
  });

  it("uses role-specific default routes", () => {
    expect(defaultRouteForRole("DESIGNER")).toBe("/scenarios");
    expect(defaultRouteForRole("MONITOR")).toBe("/");
    expect(defaultRouteForRole("ADMIN")).toBe("/admin");
  });
});
