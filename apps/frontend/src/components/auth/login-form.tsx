"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthActionError, useAuth } from "@/components/auth/auth-provider";
import { defaultRouteForRole, safeReturnTo } from "@/lib/auth/return-to";
import { env } from "@/lib/env";

const DEMO_ACCOUNTS = [
  { role: "Designer", email: "designer@example.com", password: "Designer123!" },
  { role: "Monitor", email: "monitor@example.com", password: "Monitor123!" },
] as const;

export function LoginForm({
  returnTo,
  reason,
  showDemoAccounts = env.showDemoCredentials,
}: {
  returnTo?: string;
  reason?: string;
  showDemoAccounts?: boolean;
}) {
  const router = useRouter();
  const { user, login, isLoading, error: authError } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      router.replace(safeReturnTo(returnTo, defaultRouteForRole(user.role)));
    }
  }, [returnTo, router, user]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");

    setSubmitting(true);
    setFormError(null);
    try {
      const currentUser = await login(email, password);
      router.replace(safeReturnTo(returnTo, defaultRouteForRole(currentUser.role)));
      router.refresh();
    } catch (cause) {
      setFormError(
        cause instanceof AuthActionError
          ? cause.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const disabled = submitting || isLoading;

  async function copyCredential(label: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(label);
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <div className="brand-mark">R11</div>
          <div>
            <strong>RAV-11</strong>
            <span>FACTORY TWIN</span>
          </div>
        </div>
        <div className="eyebrow">Secure operations workspace</div>
        <h1 id="login-title">Sign in</h1>

        {showDemoAccounts && <section className="demo-accounts" aria-labelledby="demo-accounts-title">
          <div className="demo-accounts-head">
            <h2 id="demo-accounts-title">Demo accounts</h2>
            <span>For evaluator access</span>
          </div>
          {DEMO_ACCOUNTS.map((account) => <article className="demo-account" key={account.role}>
            <div className="demo-account-title">
              <strong>{account.role}</strong>
              <button type="button" aria-label={`Use ${account.role} account`} onClick={() => {
                setEmail(account.email);
                setPassword(account.password);
              }}>Use this account</button>
            </div>
            {(["email", "password"] as const).map((field) => {
              const label = `${account.role} ${field}`;
              return <div className="demo-credential" key={field}>
                <span>{field}</span>
                <code>{account[field]}</code>
                <button type="button" aria-label={`Copy ${label}`}
                  onClick={() => void copyCredential(label, account[field])}>
                  {copied === label ? "Copied" : "Copy"}
                </button>
              </div>;
            })}
          </article>)}
        </section>}

        {reason === "session_expired" && (
          <div className="login-notice">Your session expired. Sign in again to continue.</div>
        )}
        {reason === "access_revoked" && (
          <div className="login-notice">This account is inactive or no longer has application access.</div>
        )}
        {(formError || authError) && (
          <div className="login-error" role="alert">{formError ?? authError}</div>
        )}

        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              disabled={disabled}
            />
          </div>
          <div className="field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              disabled={disabled}
            />
          </div>
          <button className="button primary login-submit" type="submit" disabled={disabled}>
            {submitting ? "Signing in…" : isLoading ? "Restoring session…" : "Sign in"}
          </button>
        </form>
        <small>Roles are assigned by the server and cannot be selected here.</small>
      </section>
    </main>
  );
}
