"use client";

import { useEffect } from "react";
import { fixtureRobots } from "@/lib/fixtures";
import { FactoryScene } from "@/components/factory/scene/factory-scene";
import type { Robot } from "@/schemas/robot";
import { defaultFactoryLayout, stationByType } from "@/lib/factory-layout";

const batteryBuffer = stationByType(defaultFactoryLayout, "BATTERY_BUFFER");
const marriageStation = stationByType(defaultFactoryLayout, "MARRIAGE_STATION");
const chargingStation = stationByType(defaultFactoryLayout, "CHARGING_STATION");

// Poses that put an AMR at each place the scene has to look right.
const robots: Robot[] = [
  { ...fixtureRobots[0], id: "AMR-01", status: "DELIVERING", pose: { x: 40, y: 20, yaw: 0 }, payload_id: "BP-1" },
  { ...fixtureRobots[1], id: "AMR-02", status: "PICKING", pose: { ...batteryBuffer, yaw: 0 }, payload_id: null },
  { ...fixtureRobots[2], id: "AMR-03", status: "DROPPING", pose: { ...marriageStation, yaw: 0 }, payload_id: "BP-3" },
  { ...fixtureRobots[3], id: "AMR-04", status: "CHARGING", battery: 14, pose: { ...chargingStation, yaw: Math.PI / 2 }, payload_id: null },
  { ...fixtureRobots[4], id: "AMR-05", status: "MOVING_TO_CHARGER", battery: 17, pose: { x: 35, y: 15, yaw: 2.4 }, payload_id: null },
];

export default function SceneProbe() {
  useEffect(() => { document.title = "scene-probe"; }, []);
  return <div
    data-testid="scene-probe" data-robot-count={robots.length}
    style={{ width: "100vw", height: "100vh" }}
  >
    <div className="factory-map" style={{ width: "100%", height: "100%" }}>
      <FactoryScene
        robots={robots} selectedRobotId="AMR-03" onSelect={() => undefined}
        bufferStock={4} resetSignal={0} layout={defaultFactoryLayout}
        layers={{ stations: true, routes: true, noGoZones: true }}
      />
    </div>
  </div>;
}
