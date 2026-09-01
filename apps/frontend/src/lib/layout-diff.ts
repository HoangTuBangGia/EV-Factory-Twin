import type { LayoutVersionContent } from "@/schemas/layout";

export interface LayoutChange {
  label: string;
  detail: string;
}

type Zone = { id: string; points: { x: number; y: number }[]; delay_multiplier?: number };

const CONFIG_LABELS = {
  robot_count: "Robot count",
  demand_interval_seconds: "Demand interval (s)",
  robot_speed_mps: "Robot speed (m/s)",
  charger_count: "Charger count",
} as const;

function metres(value: number) {
  return Math.round(value * 100) / 100;
}

function samePath(left: Zone["points"], right: Zone["points"]) {
  return left.length === right.length
    && left.every((point, index) => point.x === right[index].x && point.y === right[index].y);
}

function diffZones(kind: string, current: Zone[], candidate: Zone[]): LayoutChange[] {
  const before = new Map(current.map((zone) => [zone.id, zone]));
  const changes: LayoutChange[] = [];

  for (const zone of candidate) {
    const previous = before.get(zone.id);
    if (!previous) {
      changes.push({ label: `${kind} added`, detail: zone.id });
      continue;
    }
    if (!samePath(previous.points, zone.points)) {
      changes.push({ label: `${kind} reshaped`, detail: zone.id });
    }
    if (previous.delay_multiplier !== zone.delay_multiplier) {
      changes.push({
        label: `${kind} delay changed`,
        detail: `${zone.id}: ×${previous.delay_multiplier} → ×${zone.delay_multiplier}`,
      });
    }
  }

  const after = new Set(candidate.map((zone) => zone.id));
  for (const zone of current) {
    if (!after.has(zone.id)) changes.push({ label: `${kind} removed`, detail: zone.id });
  }

  return changes;
}

/**
 * Explains a layout revision in physical terms, because KPI deltas alone do not
 * say what actually moved. Both sides are immutable revisions, so a plain
 * field-by-field comparison is enough — no history walk is needed.
 */
export function diffLayoutContent(
  current: LayoutVersionContent,
  candidate: LayoutVersionContent,
): LayoutChange[] {
  const changes: LayoutChange[] = [];

  if (current.width !== candidate.width || current.height !== candidate.height) {
    changes.push({
      label: "Factory footprint",
      detail: `${current.width}×${current.height} m → ${candidate.width}×${candidate.height} m`,
    });
  }

  const currentStations = new Map(current.stations.map((station) => [station.id, station]));
  for (const station of candidate.stations) {
    const previous = currentStations.get(station.id);
    if (!previous) {
      changes.push({ label: "Station added", detail: `${station.id} · ${station.type}` });
      continue;
    }
    const distance = Math.hypot(station.x - previous.x, station.y - previous.y);
    if (distance > 0) {
      changes.push({ label: "Station moved", detail: `${station.id} by ${metres(distance)} m` });
    }
  }
  const candidateStations = new Set(candidate.stations.map((station) => station.id));
  for (const station of current.stations) {
    if (!candidateStations.has(station.id)) {
      changes.push({ label: "Station removed", detail: station.id });
    }
  }

  const currentRoutes = new Map(current.routes.map((route) => [route.id, route]));
  for (const route of candidate.routes) {
    const previous = currentRoutes.get(route.id);
    if (!previous) {
      changes.push({
        label: "Route added",
        detail: `${route.id} · ${route.start_station_id} → ${route.end_station_id}`,
      });
      continue;
    }
    if (previous.start_station_id !== route.start_station_id
      || previous.end_station_id !== route.end_station_id) {
      changes.push({
        label: "Route endpoints changed",
        detail: `${route.id}: ${previous.start_station_id} → ${previous.end_station_id}`
          + ` becomes ${route.start_station_id} → ${route.end_station_id}`,
      });
    } else if (!samePath(previous.waypoints, route.waypoints)) {
      changes.push({
        label: "Route rerouted",
        detail: `${route.id}: ${previous.waypoints.length} → ${route.waypoints.length} waypoints`,
      });
    }
  }
  const candidateRoutes = new Set(candidate.routes.map((route) => route.id));
  for (const route of current.routes) {
    if (!candidateRoutes.has(route.id)) {
      changes.push({ label: "Route removed", detail: route.id });
    }
  }

  changes.push(...diffZones("No-go zone", current.no_go_zones, candidate.no_go_zones));
  changes.push(...diffZones("Congestion zone", current.congestion_zones, candidate.congestion_zones));

  for (const field of ["robot_count", "demand_interval_seconds", "robot_speed_mps", "charger_count"] as const) {
    if (current.config[field] !== candidate.config[field]) {
      changes.push({
        label: CONFIG_LABELS[field],
        detail: `${current.config[field]} → ${candidate.config[field]}`,
      });
    }
  }

  return changes;
}
