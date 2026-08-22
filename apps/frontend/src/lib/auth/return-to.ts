import type { AppRole } from "@/schemas/auth";

export function defaultRouteForRole(role: AppRole) {
  if (role === "DESIGNER") return "/scenarios";
  return "/";
}

export function safeReturnTo(value: string | null | undefined, fallback = "/") {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return fallback;
  }

  try {
    const parsed = new URL(value, "https://factory-twin.local");
    if (parsed.origin !== "https://factory-twin.local" || parsed.pathname === "/login") {
      return fallback;
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}
