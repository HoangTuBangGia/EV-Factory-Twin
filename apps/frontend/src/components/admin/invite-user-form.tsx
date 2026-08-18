"use client";

import { type FormEvent, useState } from "react";
import {
  adminInviteRequestSchema,
  type AdminInviteRequest,
} from "@/schemas/admin";

type FieldName = keyof AdminInviteRequest;
type FieldErrors = Partial<Record<FieldName, string>>;

interface InviteUserFormProps {
  busy: boolean;
  error: string | null;
  onInvite: (invite: AdminInviteRequest) => Promise<boolean>;
}

export function InviteUserForm({ busy, error, onInvite }: InviteUserFormProps) {
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const parsed = adminInviteRequestSchema.safeParse({
      email: data.get("email"),
      display_name: data.get("display_name"),
      role: data.get("role"),
    });
    if (!parsed.success) {
      const nextErrors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const field = issue.path[0] as FieldName | undefined;
        if (field && !nextErrors[field]) nextErrors[field] = issue.message;
      }
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    if (await onInvite(parsed.data)) form.reset();
  }

  return (
    <form className="panel-body" onSubmit={submit} noValidate>
      {error && <div className="scenario-error admin-form-error" role="alert">{error}</div>}
      <div className="form-grid">
        <div className="field field-wide">
          <label htmlFor="invite-email">Email</label>
          <input id="invite-email" name="email" type="email" autoComplete="off" required />
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </div>
        <div className="field">
          <label htmlFor="invite-name">Display name</label>
          <input id="invite-name" name="display_name" autoComplete="off" required />
          {fieldErrors.display_name && <span className="field-error">{fieldErrors.display_name}</span>}
        </div>
        <div className="field">
          <label htmlFor="invite-role">Role</label>
          <select id="invite-role" name="role" defaultValue="DESIGNER">
            <option value="DESIGNER">DESIGNER</option>
            <option value="MONITOR">MONITOR</option>
            <option value="ADMIN">ADMIN</option>
          </select>
          {fieldErrors.role && <span className="field-error">{fieldErrors.role}</span>}
        </div>
      </div>
      <p className="form-help">
        Supabase sends the account setup invitation. This application never asks for,
        displays, or stores a user password.
      </p>
      <div className="button-row">
        <button className="button primary" type="submit" disabled={busy}>
          {busy ? "Sending invitation…" : "Invite user"}
        </button>
      </div>
    </form>
  );
}
