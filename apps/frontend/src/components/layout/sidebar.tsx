"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { can, type Permission } from "@/lib/auth/permissions";
import { usesMockData } from "@/lib/env";

const links: Array<{ label: string; href: string; permission: Permission }> = [
  { label: "Overview", href: "/", permission: "operations:view" },
  { label: "Factory", href: "/factory", permission: "operations:view" },
  { label: "Fleet", href: "/fleet", permission: "operations:view" },
  { label: "Tasks", href: "/tasks", permission: "operations:view" },
  { label: "Analytics", href: "/analytics", permission: "operations:view" },
  { label: "Layouts", href: "/layouts", permission: "layout:edit" },
  { label: "Scenarios", href: "/scenarios", permission: "scenarios:view" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const visibleLinks = links.filter((link) => can(user?.role, link.permission));

  return (
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">R11</div><div><strong>RAV-11</strong><span>FACTORY TWIN</span></div></div>
      <nav className="nav">
        {visibleLinks.map(({ label, href }) => (
          <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}>{label}</Link>
        ))}
      </nav>
      <div className="sidebar-foot">SIMULATION ENVIRONMENT<br/>v0.1.0 · {usesMockData ? "FIXTURE" : "API"}</div>
    </aside>
  );
}
