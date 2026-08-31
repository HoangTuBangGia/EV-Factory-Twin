"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import type { Command } from "@/schemas/command";
import { useFactoryStore } from "@/stores/factory-store";

function timestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

function canRetry(command: Command) {
  return ["REQUIRES_RELAUNCH", "FAILED", "TIMED_OUT"].includes(command.status)
    && command.attempts.length <= command.max_retries;
}

export default function CommandsPage() {
  const { user } = useAuth();
  const commandsById = useFactoryStore((state) => state.commands);
  const setCommands = useFactoryStore((state) => state.setCommands);
  const updateCommand = useFactoryStore((state) => state.updateCommand);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const commands = useMemo(() => Object.values(commandsById).sort((left, right) => (
    Date.parse(right.created_at) - Date.parse(left.created_at)
  )), [commandsById]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCommands(await apiClient.getCommands());
    } catch (cause) {
      setError(`Unable to load command history: ${message(cause)}`);
    } finally {
      setLoading(false);
    }
  }, [setCommands]);

  useEffect(() => { void load(); }, [load]);

  if (!user) return null;
  const mayRetry = can(user.role, "commands:retry");

  async function retry(command: Command) {
    if (!mayRetry || !canRetry(command)) return;
    setRetrying(command.operation_id);
    setError(null);
    try {
      updateCommand(await apiClient.retryCommand(command.operation_id));
    } catch (cause) {
      setError(`Unable to retry command: ${message(cause)}`);
      await load();
    } finally {
      setRetrying(null);
    }
  }

  return <>
    <header className="page-head">
      <div><h2>Edge commands</h2><p>Durable scenario and transport-task delivery from Backend to ROS.</p></div>
      <button className="button" type="button" disabled={loading} onClick={() => void load()}>
        {loading ? "Refreshing…" : "Refresh"}
      </button>
    </header>

    {error && <div className="scenario-error" role="alert">{error}</div>}
    {loading && commands.length === 0 && <section className="panel empty">Loading command history…</section>}
    {!loading && commands.length === 0 && <section className="panel empty">No edge command has been created.</section>}

    <div className="command-list">{commands.map((command) => {
      const retriesUsed = Math.max(0, command.attempts.length - 1);
      const retryAvailable = canRetry(command);
      return <section className="panel command-card" key={command.operation_id}>
        <div className="panel-head">
          <div><h3>{command.scenario_id ?? command.task_id}</h3><small className="command-operation">{command.command_type} · {command.operation_id}</small></div>
          <span className={`scenario-status ${command.status}`}>{command.status}</span>
        </div>
        <div className="scenario-summary command-summary">
          <div><small>Created</small><strong>{timestamp(command.created_at)}</strong></div>
          <div><small>Timeout</small><strong>{command.timeout_seconds}s</strong></div>
          <div><small>Retry budget</small><strong>{retriesUsed}/{command.max_retries}</strong></div>
          <div><small>Updated</small><strong>{timestamp(command.updated_at)}</strong></div>
        </div>
        <div className="table-wrap"><table className="data-table"><thead><tr>
          <th>Attempt</th><th>Status</th><th>Bridge</th><th>Lease expiry</th><th>Acknowledged</th><th>Completed</th><th>Detail</th>
        </tr></thead><tbody>{command.attempts.map((attempt) => <tr key={attempt.attempt_number}>
          <td>#{attempt.attempt_number}</td><td>{attempt.status}</td><td>{attempt.leased_by ?? "—"}</td>
          <td>{timestamp(attempt.lease_expires_at)}</td><td>{timestamp(attempt.acknowledged_at)}</td>
          <td>{timestamp(attempt.completed_at)}</td><td>{attempt.detail || "—"}</td>
        </tr>)}</tbody></table></div>
        {mayRetry && <div className="button-row">
          <button className="button primary" type="button"
            disabled={!retryAvailable || retrying !== null}
            title={!retryAvailable ? "Retry requires REQUIRES_RELAUNCH/FAILED/TIMED_OUT status and remaining budget" : undefined}
            onClick={() => void retry(command)}>
            {retrying === command.operation_id ? "Retrying…" : "Retry command"}
          </button>
        </div>}
      </section>;
    })}</div>
  </>;
}
