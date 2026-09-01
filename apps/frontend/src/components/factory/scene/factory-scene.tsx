"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { stationByType } from "@/lib/factory-layout";
import type { FactoryLayout } from "@/schemas/factory";
import type { Robot } from "@/schemas/robot";
import type { FactoryMapLayers } from "../factory-map";
import { Amr } from "./amr";
import { BatteryBuffer } from "./battery-buffer";
import { ChargingStation } from "./charging-station";
import { CongestionZone } from "./congestion-zone";
import { MarriageStation } from "./marriage-station";
import { NoGoZone } from "./no-go-zone";
import { RouteLanes } from "./route-lanes";
import { EvFactoryEnvironment } from "./ev-factory-environment";

const LOW_POWER_FRAME_INTERVAL_MS = 1_000 / 30;

/** Cap idle rendering while keeping camera interaction immediately responsive. */
function LowPowerFrameLoop() {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    let frameId = 0;
    let lastFrame = 0;
    function scheduleFrame(timestamp: number) {
      if (timestamp - lastFrame >= LOW_POWER_FRAME_INTERVAL_MS) {
        lastFrame = timestamp;
        invalidate();
      }
      frameId = requestAnimationFrame(scheduleFrame);
    }
    frameId = requestAnimationFrame(scheduleFrame);
    return () => cancelAnimationFrame(frameId);
  }, [invalidate]);

  return null;
}

function CameraRig({ resetSignal }: { resetSignal: number }) {
  const controls = useRef<OrbitControlsImpl>(null);

  useEffect(() => {
    if (!resetSignal) return;
    controls.current?.reset();
  }, [resetSignal]);

  return <OrbitControls
    ref={controls} makeDefault target={[0, 2.5, 0]}
    enablePan enableDamping dampingFactor={0.08}
    minDistance={8} maxDistance={190}
    minPolarAngle={0.08} maxPolarAngle={1.48}
    rotateSpeed={0.62} zoomSpeed={0.75}
  />;
}

export interface FactorySceneProps {
  robots: Robot[];
  selectedRobotId: string | null;
  onSelect: (id: string | null) => void;
  bufferStock: number;
  resetSignal: number;
  layers: FactoryMapLayers;
  layout: FactoryLayout;
}

export function FactoryScene({
  robots, selectedRobotId, onSelect, bufferStock, resetSignal, layers, layout,
}: FactorySceneProps) {
  const batteryBuffer = stationByType(layout, "BATTERY_BUFFER");
  const marriageStations = layout.stations.filter(
    (station) => station.type === "MARRIAGE_STATION",
  );
  const chargingStation = stationByType(layout, "CHARGING_STATION");
  const chargingCount = robots.filter((robot) => robot.status === "CHARGING").length;
  const joining = robots.some((robot) => robot.status === "DROPPING");

  const homePosition: [number, number, number] = [-8, 58, 82];

  return <Canvas
    frameloop="demand" shadows="basic" dpr={[0.75, 1.25]}
    camera={{ position: homePosition, fov: 43, near: 0.5, far: 360 }}
    gl={{ antialias: true, powerPreference: "high-performance" }}
    onPointerMissed={() => onSelect(null)}
  >
    <color attach="background" args={["#0f172a"]}/>
    <fog attach="fog" args={["#0f172a", 95, 245]}/>
    <LowPowerFrameLoop/>
    <CameraRig resetSignal={resetSignal}/>

    <EvFactoryEnvironment layers={layers}/>
    {layers.routes && <RouteLanes routes={layout.routes} layout={layout}/>}
    {layers.stations && <>
      <BatteryBuffer stockLevel={bufferStock} station={batteryBuffer} layout={layout}/>
      {marriageStations.map((station) => <MarriageStation
        key={station.id} joining={joining} station={station} layout={layout}
      />)}
      <ChargingStation occupied={chargingCount} station={chargingStation} layout={layout}/>
    </>}
    {layers.noGoZones && layout.no_go_zones.map((zone) => (
      <NoGoZone key={zone.id} zone={zone} layout={layout}/>
    ))}
    {layers.congestionZones && layout.congestion_zones.map((zone) => (
      <CongestionZone key={zone.id} zone={zone} layout={layout}/>
    ))}

    {robots.map((robot) => <Amr
      key={robot.id} robot={robot}
      selected={selectedRobotId === robot.id} onSelect={onSelect} layout={layout}
    />)}

  </Canvas>;
}
