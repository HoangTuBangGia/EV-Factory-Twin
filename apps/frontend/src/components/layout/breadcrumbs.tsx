"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { breadcrumbItems, type BreadcrumbItem } from "@/lib/navigation";

export function BreadcrumbTrail({ items }: { items: BreadcrumbItem[] }) {
  const truncate = items.length > 3;
  return <nav className="breadcrumbs" aria-label="Breadcrumb">
    <ol>
      {items.map((item, index) => <li key={`${item.label}-${index}`}
        className={truncate && index > 0 && index < items.length - 2
          ? "breadcrumb-mobile-hidden"
          : undefined}>
        {truncate && index === items.length - 2
          && <span className="breadcrumb-mobile-ellipsis" aria-hidden="true">…</span>}
        {item.href && index < items.length - 1
          ? <Link href={item.href}>{item.label}</Link>
          : <span aria-current={index === items.length - 1 ? "page" : undefined}>{item.label}</span>}
      </li>)}
    </ol>
  </nav>;
}

export function Breadcrumbs() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  return <BreadcrumbTrail items={breadcrumbItems(pathname, searchParams)}/>;
}
