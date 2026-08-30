import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { breadcrumbItems } from "@/lib/navigation";
import { Breadcrumbs, BreadcrumbTrail } from "./breadcrumbs";

const navigation = vi.hoisted(() => ({ pathname: "/scenarios", search: "" }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

describe("breadcrumbs", () => {
  it("derives known, deep, and fallback routes", () => {
    expect(breadcrumbItems("/fleet", new URLSearchParams())).toEqual([{ label: "Fleet" }]);
    expect(breadcrumbItems(
      "/scenarios",
      new URLSearchParams("candidate=candidate-01"),
    )).toEqual([
      { label: "Scenarios", href: "/scenarios" },
      { label: "candidate-01" },
    ]);
    expect(breadcrumbItems("/layouts/", new URLSearchParams("id=LAYOUT-01"))).toEqual([
      { label: "Layouts", href: "/layouts" },
      { label: "LAYOUT-01" },
    ]);
    expect(breadcrumbItems("/maintenance-log", new URLSearchParams()))
      .toEqual([{ label: "Maintenance log" }]);
  });

  it("renders the parent as a link and the current candidate as plain text", () => {
    navigation.pathname = "/scenarios";
    navigation.search = "candidate=SCN-OPT-01";
    render(<Breadcrumbs/>);

    expect(screen.getByRole("link", { name: "Scenarios" })).toHaveAttribute("href", "/scenarios");
    expect(screen.getByText("SCN-OPT-01")).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "SCN-OPT-01" })).not.toBeInTheDocument();
  });

  it("marks middle levels for mobile truncation while preserving the full trail", () => {
    const { container } = render(<BreadcrumbTrail items={[
      { label: "Overview", href: "/" },
      { label: "Operations", href: "/operations" },
      { label: "Factory", href: "/factory" },
      { label: "AMR-01" },
    ]}/>);

    expect(screen.getByRole("navigation", { name: "Breadcrumb" }))
      .toHaveTextContent(/Overview.*Operations.*Factory.*AMR-01/);
    expect(container.querySelectorAll(".breadcrumb-mobile-hidden")).toHaveLength(1);
    expect(container.querySelector(".breadcrumb-mobile-ellipsis")).toHaveTextContent("…");
  });
});
