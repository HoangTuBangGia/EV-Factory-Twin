import type { Permission } from "@/lib/auth/permissions";

export interface NavigationItem {
  label: string;
  href: string;
  permission: Permission;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { label: "Overview", href: "/", permission: "operations:view" },
  { label: "Factory", href: "/factory", permission: "operations:view" },
  { label: "Fleet", href: "/fleet", permission: "operations:view" },
  { label: "Tasks", href: "/tasks", permission: "operations:view" },
  { label: "Analytics", href: "/analytics", permission: "operations:view" },
  { label: "Layouts", href: "/layouts", permission: "layout:edit" },
  { label: "Scenarios", href: "/scenarios", permission: "scenarios:view" },
  { label: "Commands", href: "/commands", permission: "commands:view" },
] as const;

const ROUTE_LABELS = new Map(NAVIGATION_ITEMS.map(({ href, label }) => [href, label]));

function fallbackLabel(pathname: string) {
  const segment = pathname.split("/").filter(Boolean).at(-1);
  if (!segment) return "Overview";
  return segment.replaceAll("-", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export function breadcrumbItems(
  pathname: string,
  searchParams: Pick<URLSearchParams, "get">,
): BreadcrumbItem[] {
  const normalizedPath = pathname !== "/" ? pathname.replace(/\/$/, "") : pathname;
  const label = ROUTE_LABELS.get(normalizedPath) ?? fallbackLabel(normalizedPath);
  const detail = normalizedPath === "/scenarios"
    ? searchParams.get("candidate")?.trim()
    : normalizedPath === "/layouts"
      ? searchParams.get("id")?.trim()
      : null;

  return detail
    ? [{ label, href: normalizedPath }, { label: detail }]
    : [{ label }];
}
