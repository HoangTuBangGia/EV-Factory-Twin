import { factoryLayoutSchema, type FactoryLayout } from "@/schemas/factory";
import type { LayoutVersion } from "@/schemas/layout";
import type { Scenario } from "@/schemas/scenario";

export function projectLayoutVersion(
  layout: LayoutVersion,
  activeRouteId = layout.routes.find((route) => route.kind === "DELIVERY")?.id ?? "",
): FactoryLayout {
  return factoryLayoutSchema.parse({
    id: layout.layout_id,
    name: layout.name,
    version: layout.version,
    active_route_id: activeRouteId,
    width: layout.width,
    height: layout.height,
    stations: layout.stations,
    routes: layout.routes.map(({
      id, kind, start_station_id, end_station_id, waypoints,
    }) => ({ id, kind, start_station_id, end_station_id, waypoints })),
    no_go_zones: layout.no_go_zones,
    congestion_zones: layout.congestion_zones,
    config: layout.config,
  });
}

export function latestAppliedScenario(scenarios: Scenario[]): Scenario | null {
  return scenarios
    .filter((scenario) => scenario.status === "APPLIED")
    .sort((left, right) => (
      Date.parse(right.applied_at ?? right.created_at)
      - Date.parse(left.applied_at ?? left.created_at)
    ))[0] ?? null;
}
