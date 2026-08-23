"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { can, type Permission } from "@/lib/auth/permissions";
import { usesMockData } from "@/lib/env";
import { useFactoryStore } from "@/stores/factory-store";

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
  const { user, logout } = useAuth();
  const status = useFactoryStore((state) => state.connectionStatus);
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const visibleLinks = links.filter((link) => can(user?.role, link.permission));

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    function closeOnPointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", closeOnPointerDown);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnPointerDown);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  async function signOut() {
    setSigningOut(true);
    try {
      await logout();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="nav-shell" ref={menuRef}>
      <button
        className="nav-toggle"
        type="button"
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-controls="application-navigation"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span/><span/><span/>
      </button>
      {open && <aside className="sidebar" id="application-navigation">
        <div className="brand"><div className="brand-mark">R11</div><div><strong>RAV-11</strong><span>FACTORY TWIN</span></div></div>
        <nav className="nav" aria-label="Application navigation">
          {visibleLinks.map(({ label, href }) => (
            <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}>{label}</Link>
          ))}
        </nav>
        <div className="nav-session">
          <span className={`status ${status}`}><i className="status-dot"/>{status}</span>
          {user && <div className="user-summary"><strong>{user.display_name}</strong><span>{user.role}</span></div>}
          <button className="button compact" type="button" disabled={signingOut} onClick={() => void signOut()}>
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
        <div className="sidebar-foot">SIMULATION ENVIRONMENT<br/>v0.1.0 · {usesMockData ? "FIXTURE" : "API"}</div>
      </aside>}
    </div>
  );
}
