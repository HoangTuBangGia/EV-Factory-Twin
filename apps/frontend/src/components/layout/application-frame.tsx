"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { DataProvider } from "@/components/layout/data-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { NextActionStrip } from "@/components/workflow/next-action-strip";
import { ToastContainer } from "@/components/ui/toast";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";

function SignInRedirect({ pathname }: { pathname: string }) {
  const router = useRouter();

  useEffect(() => {
    const returnTo = `${pathname}${window.location.search}${window.location.hash}`;
    router.replace(`/login?${new URLSearchParams({ returnTo }).toString()}`);
  }, [pathname, router]);

  return <main className="center-state">Redirecting to login…</main>;
}

function ProtectedAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, isLoading, error, logout, refreshUser } = useAuth();
  const isOverview = pathname === "/";

  if (isLoading) return <main className="center-state">Restoring secure session…</main>;
  if (!user) {
    if (!error) return <SignInRedirect pathname={pathname}/>;
    return (
      <main className="center-state">
        <p>{error}</p>
        <div className="button-row">
          <button className="button" type="button" onClick={() => void logout()}>Sign out</button>
          <button className="button primary" type="button" onClick={() => void refreshUser()}>Retry</button>
        </div>
      </main>
    );
  }

  return (
    <DataProvider>
      <div className={`app-shell${isOverview ? " cockpit-shell" : ""}`}>
        <Sidebar />
        <div className="workspace">
          {!isOverview && <Topbar />}
          <main className={`content${isOverview ? " cockpit-content" : ""}`}>
            <NextActionStrip floating={isOverview} />
            {children}
          </main>
        </div>
        <OnboardingTour user={user} />
        <ToastContainer />
      </div>
    </DataProvider>
  );
}

export function ApplicationFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/homepage" || pathname === "/login" || pathname === "/scene-probe") {
    return children;
  }
  return <ProtectedAppShell>{children}</ProtectedAppShell>;
}
