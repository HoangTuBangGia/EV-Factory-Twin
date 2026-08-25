"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { ApiError, apiClient, setApiAccessToken, setApiUnauthorizedHandler } from "@/lib/api-client";
import type { CurrentUser } from "@/schemas/auth";
import { useFactoryStore } from "@/stores/factory-store";

const TOKEN_KEY = "ev-twin-access-token";

interface AuthContextValue {
  user: CurrentUser | null;
  accessToken: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshSession: () => Promise<void>;
  invalidateSession: () => void;
}

export class AuthActionError extends Error {
  constructor(
    readonly code: "INVALID_CREDENTIALS" | "PROFILE" | "UNAVAILABLE",
    message: string,
  ) {
    super(message);
    this.name = "AuthActionError";
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapAuthError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    return new AuthActionError("INVALID_CREDENTIALS", "Invalid email or password.");
  }
  if (error instanceof ApiError && error.status === 403) {
    return new AuthActionError("PROFILE", "This account is inactive or does not have access.");
  }
  return new AuthActionError("UNAVAILABLE", "Authentication is temporarily unavailable.");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { replace, refresh } = useRouter();
  const pathname = usePathname();
  const pathnameRef = useRef(pathname);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  pathnameRef.current = pathname;

  const clearAuth = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setApiAccessToken(null);
    setAccessToken(null);
    setUser(null);
    setIsLoading(false);
    useFactoryStore.getState().reset();
  }, []);

  const invalidateSession = useCallback(() => {
    clearAuth();
    if (pathnameRef.current === "/scene-probe") return;
    const params = new URLSearchParams({ reason: "session_expired" });
    if (pathnameRef.current !== "/login") params.set("returnTo", pathnameRef.current);
    replace(`/login?${params.toString()}`);
    refresh();
  }, [clearAuth, refresh, replace]);

  const refreshUser = useCallback(async () => {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (!token) {
      clearAuth();
      return;
    }
    setApiAccessToken(token);
    setAccessToken(token);
    setIsLoading(true);
    try {
      setUser(await apiClient.getCurrentUser());
      setError(null);
      setIsLoading(false);
    } catch (cause) {
      clearAuth();
      setError(mapAuthError(cause).message);
      if (pathnameRef.current !== "/login") invalidateSession();
    }
  }, [clearAuth, invalidateSession]);

  useEffect(() => {
    setApiUnauthorizedHandler(invalidateSession);
    void refreshUser();
    return () => setApiUnauthorizedHandler(null);
  }, [invalidateSession, refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const response = await apiClient.login(email, password);
      sessionStorage.setItem(TOKEN_KEY, response.access_token);
      setApiAccessToken(response.access_token);
      setAccessToken(response.access_token);
      setUser(response.user);
      setIsLoading(false);
      return response.user;
    } catch (cause) {
      throw mapAuthError(cause);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
    } catch {
      // Tokens are stateless; local deletion remains authoritative for logout.
    }
    clearAuth();
    replace("/login");
    refresh();
  }, [clearAuth, refresh, replace]);

  return (
    <AuthContext.Provider value={{
      user,
      accessToken,
      isLoading,
      error,
      login,
      logout,
      refreshUser,
      refreshSession: refreshUser,
      invalidateSession,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
