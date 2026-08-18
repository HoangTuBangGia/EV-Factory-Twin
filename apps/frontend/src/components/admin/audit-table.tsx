import type { AuditEvent } from "@/schemas/admin";

function JsonChange({ event }: { event: AuditEvent }) {
  if (event.before_data === null && event.after_data === null) return <span className="muted">—</span>;
  return (
    <details className="audit-details">
      <summary>Inspect</summary>
      {event.before_data !== null && (
        <div><small>Before</small><pre>{JSON.stringify(event.before_data, null, 2)}</pre></div>
      )}
      {event.after_data !== null && (
        <div><small>After</small><pre>{JSON.stringify(event.after_data, null, 2)}</pre></div>
      )}
      <small>Request {event.request_id}</small>
    </details>
  );
}

export function AuditTable({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) return <div className="empty">No administrative events recorded.</div>;

  return (
    <div className="table-wrap">
      <table className="data-table audit-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Resource</th>
            <th>Changes</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{new Date(event.created_at).toLocaleString()}</td>
              <td><strong>{event.actor_role}</strong><small className="audit-id">{event.actor_id}</small></td>
              <td>{event.action}</td>
              <td>{event.resource_type}<small className="audit-id">{event.resource_id}</small></td>
              <td><JsonChange event={event} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
