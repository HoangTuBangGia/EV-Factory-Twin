import { FACTORY_SIZE } from "./coordinate";

export interface WorldPoint { x: number; y: number }
export interface WorldRect { x0: number; y0: number; x1: number; y1: number }

/**
 * Station anchors in factory metres, mirroring the simulator's authoritative
 * layout in apps/backend/src/ev_twin_api/core/layout.py. Keep both in sync:
 * every AMR pose the map renders is produced against these coordinates.
 */
export const STATION_ANCHOR = {
  BATTERY_BUFFER: { x: 2, y: 4 },
  INTERSECTION_A: { x: 8, y: 4 },
  INTERSECTION_B: { x: 12, y: 8 },
  MARRIAGE_STATION: { x: 16, y: 8 },
  CHARGING_STATION: { x: 2, y: 12 },
  IDLE_ZONE: { x: 5, y: 12 },
} as const satisfies Record<string, WorldPoint>;

/** Loaded pickup -> dropoff path, mirroring core/routes.py ROUTES. */
export const MAIN_ROUTE: readonly WorldPoint[] = [
  STATION_ANCHOR.BATTERY_BUFFER,
  STATION_ANCHOR.INTERSECTION_A,
  STATION_ANCHOR.INTERSECTION_B,
  STATION_ANCHOR.MARRIAGE_STATION,
];

/**
 * Floor footprints drawn for each area. Each rect contains its station anchor
 * so an AMR that reaches a station is visibly inside the matching zone, and
 * NO_GO is kept clear of every route segment the simulator can drive.
 */
export const ZONE = {
  BATTERY_BUFFER: { x0: 0.6, y0: 2.0, x1: 4.6, y1: 6.0 },
  MARRIAGE_STATION: { x0: 13.8, y0: 5.6, x1: 18.8, y1: 10.4 },
  CHARGING_STATION: { x0: 0.6, y0: 10.4, x1: 4.0, y1: 13.8 },
  IDLE_ZONE: { x0: 4.6, y0: 10.6, x1: 7.4, y1: 13.6 },
  NO_GO: { x0: 8.4, y0: 10.8, x1: 12.8, y1: 13.6 },
} as const satisfies Record<string, WorldRect>;

export const LANE_WIDTH = 1.8;
export const BUFFER_SLOT_COUNT = 6;
export const CHARGER_BAY_COUNT = 3;

/** Factory metres (y = north) to scene units (y = up, floor centred on origin). */
export function toScene(point: WorldPoint, height = 0): [number, number, number] {
  return [
    point.x - FACTORY_SIZE.width / 2,
    height,
    FACTORY_SIZE.height / 2 - point.y,
  ];
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
