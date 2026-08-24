import { factoryLayoutSchema, type FactoryLayout, type WorldPoint } from "@/schemas/factory";

export interface WorldRect { x0: number; y0: number; x1: number; y1: number }

export const defaultFactoryLayout = factoryLayoutSchema.parse({
  id: "LAYOUT-DEFAULT",
  name: "EV battery intralogistics plant",
  version: 2,
  width: 120,
  height: 40,
  stations: [
    { id: "BATTERY_BUFFER", type: "BATTERY_BUFFER", x: 32, y: 29 },
    { id: "MARRIAGE_STATION", type: "MARRIAGE_STATION", x: 52, y: 6 },
    { id: "CHARGING_STATION", type: "CHARGING_STATION", x: 32, y: 11 },
  ],
  routes: [{
    id: "BATTERY_DELIVERY",
    waypoints: [
      { x: 32, y: 29 },
      { x: 32, y: 20 },
      { x: 40, y: 20 },
      { x: 52, y: 20 },
      { x: 52, y: 6 },
    ],
  }],
  no_go_zones: [{
    id: "GIGA_PRESS_CLEARANCE",
    points: [{ x: 44, y: 27 }, { x: 58, y: 27 }, { x: 58, y: 37 }, { x: 44, y: 37 }],
  }],
});

export const LANE_WIDTH = 1.8;
export const BUFFER_SLOT_COUNT = 6;
export const CHARGER_BAY_COUNT = 3;

/** Factory metres (y = north) to scene units (y = up, floor centred on origin). */
export function toScene(
  point: WorldPoint,
  layout: Pick<FactoryLayout, "width" | "height">,
  height = 0,
): [number, number, number] {
  return [
    point.x - layout.width / 2,
    height,
    layout.height / 2 - point.y,
  ];
}

export function stationByType(
  layout: FactoryLayout,
  type: FactoryLayout["stations"][number]["type"],
) {
  const station = layout.stations.find((candidate) => candidate.type === type);
  if (!station) throw new Error(`Layout '${layout.id}' is missing station type '${type}'`);
  return station;
}

export function boundsForPoints(points: readonly WorldPoint[]): WorldRect {
  return {
    x0: Math.min(...points.map((point) => point.x)),
    y0: Math.min(...points.map((point) => point.y)),
    x1: Math.max(...points.map((point) => point.x)),
    y1: Math.max(...points.map((point) => point.y)),
  };
}

export function rectCenter(rect: WorldRect): WorldPoint {
  return { x: (rect.x0 + rect.x1) / 2, y: (rect.y0 + rect.y1) / 2 };
}

export function rectSize(rect: WorldRect): { width: number; depth: number } {
  return { width: rect.x1 - rect.x0, depth: rect.y1 - rect.y0 };
}

export function rectContains(rect: WorldRect, point: WorldPoint): boolean {
  return point.x >= rect.x0 && point.x <= rect.x1
    && point.y >= rect.y0 && point.y <= rect.y1;
}

export type { WorldPoint } from "@/schemas/factory";
