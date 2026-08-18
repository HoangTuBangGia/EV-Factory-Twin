"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminUserTable } from "@/components/admin/admin-user-table";
import { AuditTable } from "@/components/admin/audit-table";
import { InviteUserForm } from "@/components/admin/invite-user-form";
import { AccessDenied } from "@/components/auth/access-denied";
import { useAuth } from "@/components/auth/auth-provider";
import { ApiError, apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import type {
  AdminInviteRequest,
  AdminUser,
  AdminUserUpdate,
  AuditEvent,
} from "@/schemas/admin";

function safeLoadError(error: unknown) {
  if (error instanceof ApiError && error.status === 403) {
    return "Administrator access is required.";
  }
  return "Administrative data is unavailable. Check the API connection and retry.";
}

function inviteError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 501 || error.status === 503) {
      return "User invitations are unavailable because the server-side Supabase Admin integration is not configured.";
    }
    if (error.status === 409) return "An account with this email already exists.";
    if (error.status === 403) return "Your account is not allowed to invite users.";
  }
  return "The invitation could not be sent. Please retry when the authentication service is available.";
}

function AdminWorkspace({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [inviteFailure, setInviteFailure] = useState<string | null>(null);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const [nextUsers, nextEvents] = await Promise.all([
        apiClient.getAdminUsers(),
        apiClient.getAdminAudit(100),
      ]);
      setUsers(nextUsers);
      setEvents(nextEvents);
    } catch (error) {
      setPageError(safeLoadError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function refreshAudit() {
    try {
      setEvents(await apiClient.getAdminAudit(100));
    } catch {
      // The completed user operation remains visible. A manual refresh can
      // recover the audit table without pretending the update itself failed.
    }
  }

  async function updateUser(id: string, update: AdminUserUpdate) {
    setBusyUserId(id);
    setPageError(null);
    try {
      const updated = await apiClient.updateAdminUser(id, update);
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user));
      await refreshAudit();
    } catch (error) {
      setPageError(error instanceof ApiError && error.status === 409
        ? "This change would leave the application without an active administrator."
        : safeLoadError(error));
    } finally {
      setBusyUserId(null);
    }
  }

  async function inviteUser(invite: AdminInviteRequest) {
    setInviting(true);
    setInviteFailure(null);
    try {
      const invited = await apiClient.inviteAdminUser(invite);
      setUsers((current) => [invited, ...current.filter((user) => user.id !== invited.id)]);
      await refreshAudit();
      return true;
    } catch (error) {
      setInviteFailure(inviteError(error));
      return false;
    } finally {
      setInviting(false);
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h2>Administration</h2>
          <p>Manage application roles and review security-relevant changes.</p>
        </div>
        <button className="button" type="button" disabled={loading} onClick={() => void load()}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      <div className="notice admin-boundary-note">
        ADMIN is read-only for factory operations: it cannot run, approve, reject, or apply scenarios.
      </div>
      {pageError && <div className="scenario-error admin-page-error" role="alert">{pageError}</div>}

      <div className="admin-layout">
        <section className="panel">
          <div className="panel-head"><h3>Application users</h3><span>{users.length} profiles</span></div>
          {loading && users.length === 0
            ? <div className="empty">Loading users…</div>
            : <AdminUserTable users={users} currentUserId={currentUserId} busyUserId={busyUserId} onUpdate={updateUser} />}
        </section>

        <section className="panel">
          <div className="panel-head"><h3>Invite user</h3><span>Supabase Auth</span></div>
          <InviteUserForm busy={inviting} error={inviteFailure} onInvite={inviteUser} />
        </section>
      </div>

      <section className="panel admin-audit-panel">
        <div className="panel-head"><h3>Administrative audit</h3><span>Latest {events.length} events</span></div>
        {loading && events.length === 0
          ? <div className="empty">Loading audit events…</div>
          : <AuditTable events={events} />}
      </section>
    </>
  );
}

export default function AdminPage() {
  const { user } = useAuth();
  if (!user || !can(user.role, "users:manage") || !can(user.role, "audit:view")) {
    return <AccessDenied />;
  }
  return <AdminWorkspace currentUserId={user.id} />;
}
