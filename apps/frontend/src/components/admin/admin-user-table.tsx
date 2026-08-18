"use client";

import type { AdminUser, AdminUserUpdate } from "@/schemas/admin";
import type { AppRole } from "@/schemas/auth";

const roles: AppRole[] = ["DESIGNER", "MONITOR", "ADMIN"];

interface AdminUserTableProps {
  users: AdminUser[];
  currentUserId: string;
  busyUserId: string | null;
  onUpdate: (id: string, update: AdminUserUpdate) => Promise<void>;
}

export function AdminUserTable({
  users,
  currentUserId,
  busyUserId,
  onUpdate,
}: AdminUserTableProps) {
  if (users.length === 0) {
    return <div className="empty">No application users were found.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table admin-users-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const busy = busyUserId === user.id;
            return (
              <tr key={user.id}>
                <td>
                  <span className="admin-user-name">
                    {user.display_name}
                    {user.id === currentUserId && <small>YOU</small>}
                  </span>
                  <span className="admin-user-email">{user.email}</span>
                </td>
                <td>
                  <label className="sr-only" htmlFor={`role-${user.id}`}>
                    Role for {user.display_name}
                  </label>
                  <select
                    id={`role-${user.id}`}
                    className="filter admin-role-select"
                    value={user.role}
                    disabled={busy}
                    onChange={(event) => void onUpdate(user.id, {
                      role: event.currentTarget.value as AppRole,
                    })}
                  >
                    {roles.map((role) => <option key={role} value={role}>{role}</option>)}
                  </select>
                </td>
                <td>
                  <span className={`badge ${user.is_active ? "" : "OFFLINE"}`}>
                    {user.is_active ? "ACTIVE" : "INACTIVE"}
                  </span>
                </td>
                <td>{new Date(user.created_at).toLocaleString()}</td>
                <td>
                  <button
                    className={`button compact ${user.is_active ? "danger" : ""}`}
                    type="button"
                    disabled={busy}
                    onClick={() => void onUpdate(user.id, { is_active: !user.is_active })}
                  >
                    {busy ? "Saving…" : user.is_active ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
