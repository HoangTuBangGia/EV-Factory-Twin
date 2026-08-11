import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { DataProvider } from "@/components/layout/data-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export const metadata: Metadata = { title: "RAV-11 Factory Twin", description: "AMR battery intralogistics operations twin" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><DataProvider><div className="app-shell"><Sidebar/><div className="workspace"><Topbar/><main className="content">{children}</main></div></div></DataProvider></body></html>;
}
