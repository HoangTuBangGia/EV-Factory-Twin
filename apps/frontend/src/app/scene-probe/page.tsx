"use client";

import { useEffect } from "react";
import { fixtureRobots } from "@/lib/fixtures";
import { FactoryScene } from "@/components/factory/scene/factory-scene";
import type { Robot } from "@/schemas/robot";
import { STATION_ANCHOR } from "@/lib/factory-layout";

// Poses that put an AMR at each place the scene has to look right.
const robots: Robot[] = [
  { ...fixtureRobots[0], id: "AMR-01", status: "DELIVERING", pose: { x: 10, y: 6, yaw: 0.588 }, payload_id: "BP-1" },
  { ...fixtureRobots[1], id: "AMR-02", status: "PICKING", pose: { ...STATION_ANCHOR.BATTERY_BUFFER, yaw: 0 }, payload_id: null },
  { ...fixtureRobots[2], id: "AMR-03", status: "DROPPING", pose: { ...STATION_ANCHOR.MARRIAGE_STATION, yaw: 0 }, payload_id: "BP-3" },
  { ...fixtureRobots[3], id: "AMR-04", status: "CHARGING", battery: 14, pose: { ...STATION_ANCHOR.CHARGING_STATION, yaw: Math.PI / 2 }, payload_id: null },
  { ...fixtureRobots[4], id: "AMR-05", status: "MOVING_TO_CHARGER", battery: 17, pose: { x: 9, y: 6.5, yaw: 2.4 }, payload_id: null },
];

export default function SceneProbe() {
  useEffect(() => { document.title = "scene-probe"; }, []);
  return <div style={{ width: 1440, height: 900 }}>
    <div className="factory-map" style={{ height: 900 }}>
      <FactoryScene
        robots={robots} selectedRobotId="AMR-03" onSelect={() => undefined}
        bufferStock={4} resetSignal={0}
      />
    </div>
  </div>;
}
