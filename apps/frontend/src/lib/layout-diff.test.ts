import { describe, expect, it } from "vitest";
import { diffLayoutContent } from "./layout-diff";
import { fixtureLayoutVersion } from "./fixtures";
import type { LayoutVersionContent } from "@/schemas/layout";

function revision(overrides: Partial<LayoutVersionContent> = {}): LayoutVersionContent {
  return { ...fixtureLayoutVersion, ...overrides };
}

function details(current: LayoutVersionContent, candidate: LayoutVersionContent) {
  return diffLayoutContent(current, candidate).map((change) => `${change.label}: ${change.detail}`);
}

describe("diffLayoutContent", () => {
  it("reports nothing for two identical revisions", () => {
    expect(diffLayoutContent(revision(), revision())).toEqual([]);
  });

  it("measures how far a station moved", () => {
    const moved = revision({
      stations: fixtureLayoutVersion.stations.map((station) => (
        station.id === "MARRIAGE_STATION" ? { ...station, x: 63, y: 24 } : station
      )),
    });

    expect(details(revision(), moved)).toEqual(["Station moved: MARRIAGE_STATION by 5 m"]);
  });

  it("separates added and removed stations", () => {
    const [buffer, marriage, charger] = fixtureLayoutVersion.stations;
    const swapped = revision({
      stations: [buffer, marriage, { ...charger, id: "CHARGING_STATION_2" }],
    });

    expect(details(revision(), swapped)).toEqual([
      "Station added: CHARGING_STATION_2 · CHARGING_STATION",
      "Station removed: CHARGING_STATION",
    ]);
  });

  it("tells a reroute apart from an endpoint change", () => {
    const rerouted = revision({
      routes: [{
        ...fixtureLayoutVersion.routes[0],
        waypoints: [{ x: 30, y: 20 }, { x: 45, y: 30 }, { x: 60, y: 20 }],
      }],
    });
    expect(details(revision(), rerouted))
      .toEqual(["Route rerouted: BATTERY_DELIVERY: 2 → 3 waypoints"]);

    const redirected = revision({
      routes: [{ ...fixtureLayoutVersion.routes[0], end_station_id: "CHARGING_STATION" }],
    });
    expect(details(revision(), redirected)).toEqual([
      "Route endpoints changed: BATTERY_DELIVERY: BATTERY_BUFFER → MARRIAGE_STATION"
      + " becomes BATTERY_BUFFER → CHARGING_STATION",
    ]);
  });

  it("reports zone reshaping and delay changes independently", () => {
    const zone = fixtureLayoutVersion.congestion_zones[0];
    const slower = revision({
      congestion_zones: [{
        ...zone,
        delay_multiplier: 1.6,
        points: [...zone.points, { x: 38, y: 22.5 }],
      }],
    });

    expect(details(revision(), slower)).toEqual([
      "Congestion zone reshaped: WAREHOUSE_PRODUCTION_DOOR",
      "Congestion zone delay changed: WAREHOUSE_PRODUCTION_DOOR: ×1.25 → ×1.6",
    ]);
  });

  it("reports footprint and runtime configuration changes", () => {
    const resized = revision({
      width: 130,
      config: { ...fixtureLayoutVersion.config, charger_count: 4 },
    });

    expect(details(revision(), resized)).toEqual([
      "Factory footprint: 120×40 m → 130×40 m",
      "Charger count: 2 → 4",
    ]);
  });
});
