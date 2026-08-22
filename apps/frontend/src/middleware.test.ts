import { NextRequest, NextResponse } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { middleware } from "./middleware";

const mocks = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("@/lib/supabase/middleware", () => ({
  refreshSupabaseSession: mocks.refresh,
}));

describe("frontend auth middleware", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects a signed-out dashboard request and preserves returnTo", async () => {
    mocks.refresh.mockResolvedValue({ response: NextResponse.next(), user: null });
    const response = await middleware(
      new NextRequest("http://localhost:3000/factory?robot=AMR-01"),
    );

    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location")!);
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("returnTo")).toBe("/factory?robot=AMR-01");
  });

  it("keeps login public while the client restores the role", async () => {
    mocks.refresh.mockResolvedValue({ response: NextResponse.next(), user: null });
    const response = await middleware(new NextRequest("http://localhost:3000/login"));

    expect(response.status).toBe(200);
    expect(response.headers.get("location")).toBeNull();
  });

  it("allows an authenticated dashboard request", async () => {
    mocks.refresh.mockResolvedValue({
      response: NextResponse.next(),
      user: { id: "user-id" },
    });
    const response = await middleware(new NextRequest("http://localhost:3000/scenarios"));

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
  });

});
