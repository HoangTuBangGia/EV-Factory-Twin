import { describe, expect, it } from "vitest";
import { factoryLayoutSchema } from "@/schemas/factory";
import {
  boundsForPoints,
  defaultFactoryLayout,
  rectContains,
  stationByType,
  toScene,
  type WorldPoint,
} from "./factory-layout";

describe("factory layout", () => {
  it("matches the current simulator stations and delivery route", () => {
    expect(defaultFactoryLayout.stations.map(({ type, x, y }) => [type, x, y])).toEqual([
      ["BATTERY_BUFFER", 32, 29],
      ["MARRIAGE_STATION", 52, 6],
      ["MARRIAGE_STATION", 82, 8],
      ["CHARGING_STATION", 32, 11],
    ]);
    expect(defaultFactoryLayout.routes.map(({ id, kind }) => [id, kind])).toEqual([
      ["BATTERY_DELIVERY", "DELIVERY"],
      ["BATTERY_DELIVERY_LONG", "DELIVERY"],
      ["CHARGER_LINK", "SUPPORT"],
    ]);
    expect(defaultFactoryLayout.routes[0].waypoints.map(({ x, y }) => [x, y])).toEqual([
      [32, 29], [32, 20], [40, 20], [52, 20], [52, 6],
    ]);
  });

  it("rejects layout coordinates outside the factory footprint", () => {
    const result = factoryLayoutSchema.safeParse({
      ...defaultFactoryLayout,
      stations: [{
        ...defaultFactoryLayout.stations[0],
        x: defaultFactoryLayout.width + 1,
      }],
    });
    expect(result.success).toBe(false);
  });

  it("keeps the no-go zone clear of the delivery route", () => {
    const route = defaultFactoryLayout.routes[0].waypoints;
    const noGoBounds = boundsForPoints(defaultFactoryLayout.no_go_zones[0].points);
    const paths: [WorldPoint, WorldPoint][] = [];
    for (let index = 0; index < route.length - 1; index += 1) {
      paths.push([route[index], route[index + 1]]);
    }

    for (const [a, b] of paths) {
      const steps = Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / 0.05);
      for (let step = 0; step <= steps; step += 1) {
        const t = steps === 0 ? 0 : step / steps;
        const point = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
        expect(rectContains(noGoBounds, point)).toBe(false);
      }
    }
  });

  it("uses layout dimensions when converting world coordinates", () => {
    expect(toScene({ x: 60, y: 20 }, defaultFactoryLayout)).toEqual([0, 0, 0]);
    expect(toScene(
      stationByType(defaultFactoryLayout, "BATTERY_BUFFER"),
      defaultFactoryLayout,
    )).toEqual([-28, 0, -9]);
    expect(toScene({ x: 15, y: 10 }, { width: 30, height: 20 }, 1.5)).toEqual([
      0, 1.5, 0,
    ]);
  });
});
