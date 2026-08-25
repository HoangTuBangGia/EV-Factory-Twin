import { describe, expect, it } from "vitest";
import { middleware } from "./middleware";

describe("frontend middleware", () => {
  it("keeps routes uncached while client auth restores the session", () => {
    const response = middleware();
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
  });
});
