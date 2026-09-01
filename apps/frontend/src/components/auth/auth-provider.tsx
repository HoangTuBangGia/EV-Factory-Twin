"use client";

import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ApiError,
  apiClient,
  setApiAccessToken,
  setApiUnauthorizedHandler,
} from "@/lib/api-client";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type { CurrentUser } from "@/schemas/auth";
import { useFactoryStore } from "@/stores/factory-store";

interface AuthContextValue {
  user: CurrentUser | null;
  session: Session | null;
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
    readonly code: "CONFIGURATION" | "INVALID_CREDENTIALS" | "PROFILE" | "UNAVAILABLE",
    message: string,
  ) {
    super(message);
    this.name = "AuthActionError";
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

function isPublicPath(pathname: string) {
  return pathname === "/homepage" || pathname === "/login" || pathname === "/scene-probe";
}

function profileError(error: unknown) {
  if (error instanceof ApiError && error.status === 403) {
    return new AuthActionError("PROFILE", "This account is inactive or does not have access.");
  }
  if (error instanceof ApiError && error.status === 401) {
    return new AuthActionError("PROFILE", "Your session has expired. Please sign in again.");
  }
  return new AuthActionError("UNAVAILABLE", "Unable to verify your account with the Factory Twin API.");
}

function loginError(status?: number) {
  if (status === 400 || status === 401 || status === 422) {
    return new AuthActionError("INVALID_CREDENTIALS", "Invalid email or password.");
  }
  return new AuthActionError("UNAVAILABLE", "Authentication is temporarily unavailable.");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { replace, refresh: refreshRouter } = useRouter();
  const pathname = usePathname();
  const clientRef = useRef<SupabaseClient | null>(null);
  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  const pathnameRef = useRef(pathname);
  const logoutInProgressRef = useRef(false);
  const expirationInProgressRef = useRef(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  pathnameRef.current = pathname;
  if (clientRef.current === null) clientRef.current = getSupabaseBrowserClient();

  const clearAuth = useCallback(() => {
    generationRef.current += 1;
    setApiAccessToken(null);
    setSession(null);
    setUser(null);
    setIsLoading(false);
    useFactoryStore.getState().reset();
  }, []);

  const redirectToLogin = useCallback((reason: "session_expired" | "access_revoked") => {
    if (isPublicPath(pathnameRef.current)) return;
    const params = new URLSearchParams({ reason });
    if (pathnameRef.current !== "/login") params.set("returnTo", pathnameRef.current);
    replace(`/login?${params.toString()}`);
    refreshRouter();
  }, [refreshRouter, replace]);

  const terminateSession = useCallback((reason: "session_expired" | "access_revoked") => {
    if (expirationInProgressRef.current) return;
    expirationInProgressRef.current = true;
    logoutInProgressRef.current = true;
    clearAuth();
    setError(null);
    redirectToLogin(reason);

    const client = clientRef.current;
    if (!client) {
      logoutInProgressRef.current = false;
      return;
    }
    void client.auth.signOut({ scope: "local" }).finally(() => {
      logoutInProgressRef.current = false;
    });
  }, [clearAuth, redirectToLogin]);

  const expireSession = useCallback(() => {
    terminateSession("session_expired");
  }, [terminateSession]);

  const revokeAccess = useCallback(() => {
    terminateSession("access_revoked");
  }, [terminateSession]);

  const hydrateSession = useCallback(async (
    nextSession: Session | null,
    throwOnError = false,
  ): Promise<CurrentUser | null> => {
    const generation = ++generationRef.current;
    setSession(nextSession);
    setApiAccessToken(nextSession?.access_token ?? null);
    setError(null);

    if (!nextSession) {
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      const currentUser = await apiClient.getCurrentUser();
      if (!mountedRef.current || generation !== generationRef.current) return null;
      expirationInProgressRef.current = false;
      setUser(currentUser);
      setIsLoading(false);
      return currentUser;
    } catch (cause) {
      if (!mountedRef.current || generation !== generationRef.current) return null;
      const authError = profileError(cause);
      if (cause instanceof ApiError && cause.status === 403) {
        revokeAccess();
        if (throwOnError) throw authError;
        return null;
      }
      setUser(null);
      setError(authError.message);
      setIsLoading(false);
      if (throwOnError) throw authError;
      return null;
    }
  }, [revokeAccess]);

  const refreshUser = useCallback(async () => {
    const client = clientRef.current;
    if (!client) {
      setError("Supabase authentication is not configured.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    const { data, error: sessionError } = await client.auth.getSession();
    if (sessionError) {
      clearAuth();
      setError(null);
      setIsLoading(false);
      if (!isPublicPath(pathnameRef.current)) redirectToLogin("session_expired");
      return;
    }
    await hydrateSession(data.session);
    if (!data.session && !isPublicPath(pathnameRef.current)) redirectToLogin("session_expired");
  }, [clearAuth, hydrateSession, redirectToLogin]);

  const refreshSession = useCallback(async () => {
    const client = clientRef.current;
    if (!client) {
      expireSession();
      return;
    }
    const { data, error: refreshError } = await client.auth.refreshSession();
    if (refreshError || !data.session) {
      expireSession();
      return;
    }
    await hydrateSession(data.session);
  }, [expireSession, hydrateSession]);

  useEffect(() => {
    mountedRef.current = true;
    const client = clientRef.current;
    if (!client) {
      setError("Supabase authentication is not configured.");
      setIsLoading(false);
      return () => { mountedRef.current = false; };
    }

    setApiUnauthorizedHandler(expireSession);
    void refreshUser();
    const { data: { subscription } } = client.auth.onAuthStateChange((event, nextSession) => {
      if (event === "SIGNED_OUT" || !nextSession) {
        const shouldRedirect = !logoutInProgressRef.current && !isPublicPath(pathnameRef.current);
        clearAuth();
        setError(null);
        setIsLoading(false);
        if (shouldRedirect) redirectToLogin("session_expired");
        return;
      }
      queueMicrotask(() => { void hydrateSession(nextSession); });
    });

    return () => {
      mountedRef.current = false;
      setApiUnauthorizedHandler(null);
      subscription.unsubscribe();
    };
  }, [clearAuth, expireSession, hydrateSession, redirectToLogin, refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const client = clientRef.current;
    if (!client) {
      throw new AuthActionError("CONFIGURATION", "Supabase authentication is not configured.");
    }

    expirationInProgressRef.current = false;
    setError(null);
    const { data, error: signInError } = await client.auth.signInWithPassword({ email, password });
    if (signInError) throw loginError(signInError.status);
    if (!data.session) throw new AuthActionError("UNAVAILABLE", "Authentication did not return a session.");

    const currentUser = await hydrateSession(data.session, true);
    if (!currentUser) throw new AuthActionError("PROFILE", "Unable to load your Factory Twin profile.");
    return currentUser;
  }, [hydrateSession]);

  const logout = useCallback(async () => {
    const client = clientRef.current;
    logoutInProgressRef.current = true;
    expirationInProgressRef.current = false;
    clearAuth();
    setError(null);
    try {
      if (client) await client.auth.signOut({ scope: "local" });
    } catch {
      // Local application state is already cleared. Navigation must not be
      // blocked if the auth service is temporarily unavailable during logout.
    } finally {
      replace("/login");
      refreshRouter();
      logoutInProgressRef.current = false;
    }
  }, [clearAuth, refreshRouter, replace]);

  return (
    <AuthContext.Provider value={{
      user,
      session,
      accessToken: session?.access_token ?? null,
      isLoading,
      error,
      login,
      logout,
      refreshUser,
      refreshSession,
      invalidateSession: expireSession,
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
