import { describe, expect, it } from "vitest";
import { FACTORY_SIZE } from "./coordinate";
import {
  MAIN_ROUTE, rectContains, STATION_ANCHOR, toScene, ZONE, type WorldPoint,
} from "./factory-layout";

describe("factory layout", () => {
  // These mirror apps/backend/src/ev_twin_api/core/layout.py and core/routes.py.
  // A drift here means the map paints lanes the simulator never drives on.
  it("matches the simulator station anchors", () => {
    expect(STATION_ANCHOR).toEqual({
      BATTERY_BUFFER: { x: 2, y: 4 },
      INTERSECTION_A: { x: 8, y: 4 },
      INTERSECTION_B: { x: 12, y: 8 },
      MARRIAGE_STATION: { x: 16, y: 8 },
      CHARGING_STATION: { x: 2, y: 12 },
      IDLE_ZONE: { x: 5, y: 12 },
    });
  });

  it("matches the simulator pickup to dropoff route", () => {
    expect(MAIN_ROUTE.map((point) => [point.x, point.y])).toEqual([
      [2, 4], [8, 4], [12, 8], [16, 8],
    ]);
  });

  it("keeps every zone inside the factory footprint", () => {
    for (const [name, rect] of Object.entries(ZONE)) {
      expect(rect.x0, name).toBeGreaterThanOrEqual(0);
      expect(rect.y0, name).toBeGreaterThanOrEqual(0);
      expect(rect.x1, name).toBeLessThanOrEqual(FACTORY_SIZE.width);
      expect(rect.y1, name).toBeLessThanOrEqual(FACTORY_SIZE.height);
      expect(rect.x1, name).toBeGreaterThan(rect.x0);
      expect(rect.y1, name).toBeGreaterThan(rect.y0);
    }
  });

  it("draws each station zone around its own anchor", () => {
    for (const station of ["BATTERY_BUFFER", "MARRIAGE_STATION", "CHARGING_STATION", "IDLE_ZONE"] as const) {
      expect(rectContains(ZONE[station], STATION_ANCHOR[station]), station).toBe(true);
    }
  });

  it("keeps the no-go zone clear of every drivable path", () => {
    const charger = STATION_ANCHOR.CHARGING_STATION;
    const paths: [WorldPoint, WorldPoint][] = [];
    for (let i = 0; i < MAIN_ROUTE.length - 1; i += 1) {
      paths.push([MAIN_ROUTE[i], MAIN_ROUTE[i + 1]]);
    }
    // A charging robot drives straight to the charger from wherever it stands.
    for (const anchor of Object.values(STATION_ANCHOR)) paths.push([anchor, charger]);

    // Walk each path at 5 cm and assert no sample ever lands inside NO_GO.
    for (const [a, b] of paths) {
      const steps = Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / 0.05);
      for (let step = 0; step <= steps; step += 1) {
        const t = steps === 0 ? 0 : step / steps;
        const point = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
        expect(rectContains(ZONE.NO_GO, point), `${JSON.stringify(point)} on ${JSON.stringify([a, b])}`)
          .toBe(false);
      }
    }
  });

  it("centres the floor on the origin and flips north to -z", () => {
    expect(toScene({ x: 10, y: 7.5 })).toEqual([0, 0, 0]);
    expect(toScene(STATION_ANCHOR.BATTERY_BUFFER)).toEqual([-8, 0, 3.5]);
    expect(toScene(STATION_ANCHOR.MARRIAGE_STATION, 1.5)).toEqual([6, 1.5, -0.5]);
  });
});
