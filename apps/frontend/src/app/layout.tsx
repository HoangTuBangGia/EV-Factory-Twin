import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { ApplicationFrame } from "@/components/layout/application-frame";

export const metadata: Metadata = { title: "RAV-11 Factory Twin", description: "AMR battery intralogistics operations twin" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ApplicationFrame>{children}</ApplicationFrame>
        </AuthProvider>
      </body>
    </html>
  );
}
