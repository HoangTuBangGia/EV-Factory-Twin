import { factoryLayoutSchema, type FactoryLayout } from "@/schemas/factory";
import type { LayoutVersion } from "@/schemas/layout";
import type { Scenario } from "@/schemas/scenario";

export function projectLayoutVersion(layout: LayoutVersion): FactoryLayout {
  return factoryLayoutSchema.parse({
    id: layout.layout_id,
    name: layout.name,
    version: layout.version,
    width: layout.width,
    height: layout.height,
    stations: layout.stations,
    routes: layout.routes.map(({ id, waypoints }) => ({ id, waypoints })),
    no_go_zones: layout.no_go_zones,
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
