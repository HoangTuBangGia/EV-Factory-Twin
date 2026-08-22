"use client";

import { ContactShadows, Grid, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { stationByType } from "@/lib/factory-layout";
import type { FactoryLayout } from "@/schemas/factory";
import type { Robot } from "@/schemas/robot";
import type { FactoryMapLayers } from "../factory-map";
import { Amr } from "./amr";
import { BatteryBuffer } from "./battery-buffer";
import { ChargingStation } from "./charging-station";
import { MarriageStation } from "./marriage-station";
import { NoGoZone } from "./no-go-zone";
import { ChargerApproach, RouteLanes } from "./route-lanes";
import { BuildingShell } from "./shell";
import { concreteColorTexture, concreteRoughnessTexture } from "./textures";

/** Sealed-concrete slab with a metre grid and 5 m section joints. */
function FactoryFloor({ width, depth }: { width: number; depth: number }) {
  const colorMap = useMemo(() => concreteColorTexture(), []);
  const roughnessMap = useMemo(() => concreteRoughnessTexture(), []);

  return <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[width, depth]}/>
      <meshStandardMaterial
        map={colorMap} roughnessMap={roughnessMap} color="#20343d"
        roughness={0.72} metalness={0.16}
      />
    </mesh>
    <Grid
      args={[width, depth]} position={[0, 0.004, 0]}
      cellSize={1} cellThickness={0.5} cellColor="#1d3a45"
      sectionSize={5} sectionThickness={1.1} sectionColor="#2c5f6d"
      fadeDistance={58} fadeStrength={1.1} side={THREE.DoubleSide}
    />
  </group>;
}

function Lighting() {
  const light = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    const shadow = light.current?.shadow;
    if (shadow) {
      shadow.camera.left = -16; shadow.camera.right = 16;
      shadow.camera.top = 14; shadow.camera.bottom = -14;
      shadow.camera.near = 1; shadow.camera.far = 48;
      shadow.camera.updateProjectionMatrix();
    }
  }, []);

  return <>
    <ambientLight intensity={0.5} color="#8fb8c4"/>
    <hemisphereLight args={["#5fd8c4", "#0a1a22", 0.55]}/>
    <directionalLight
      ref={light} position={[11, 19, 9]} intensity={1.35} color="#dbf1f7"
      castShadow shadow-mapSize={[2048, 2048]} shadow-bias={-0.0008} shadow-normalBias={0.02}
    />
    <directionalLight position={[-13, 9, -8]} intensity={0.35} color="#4fb3d9"/>
    <pointLight position={[0, 6, 0]} intensity={16} distance={26} decay={2} color="#2f6f80"/>
  </>;
}

function CameraRig({ resetSignal }: { resetSignal: number }) {
  const controls = useRef<OrbitControlsImpl>(null);

  useEffect(() => {
    if (!resetSignal) return;
    controls.current?.reset();
  }, [resetSignal]);

  return <OrbitControls
    ref={controls} makeDefault target={[0, 0.4, 0]}
    enablePan={false} enableDamping dampingFactor={0.08}
    minDistance={9} maxDistance={44}
    minPolarAngle={0.12} maxPolarAngle={1.36}
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
  const marriageStation = stationByType(layout, "MARRIAGE_STATION");
  const chargingStation = stationByType(layout, "CHARGING_STATION");
  const chargingCount = robots.filter((robot) => robot.status === "CHARGING").length;
  const joining = robots.some((robot) => robot.status === "DROPPING");
  const approaching = robots.filter((robot) => robot.status === "MOVING_TO_CHARGER");

  const homePosition: [number, number, number] = [
    -layout.width * 0.16,
    Math.max(15.5, layout.height),
    Math.max(19.5, layout.width),
  ];

  return <Canvas
    shadows="percentage" dpr={[1, 1.85]} camera={{ position: homePosition, fov: 40, near: 0.5, far: 140 }}
    gl={{ antialias: true, powerPreference: "high-performance" }}
    onPointerMissed={() => onSelect(null)}
  >
    <color attach="background" args={["#060f15"]}/>
    <fog attach="fog" args={["#060f15", 30, 74]}/>
    <Lighting/>
    <CameraRig resetSignal={resetSignal}/>

    <FactoryFloor width={layout.width} depth={layout.height}/>
    <BuildingShell width={layout.width} depth={layout.height}/>
    {layers.routes && <RouteLanes routes={layout.routes} layout={layout}/>}
    {layers.stations && <>
      <BatteryBuffer stockLevel={bufferStock} station={batteryBuffer} layout={layout}/>
      <MarriageStation joining={joining} station={marriageStation} layout={layout}/>
      <ChargingStation occupied={chargingCount} station={chargingStation} layout={layout}/>
    </>}
    {layers.noGoZones && layout.no_go_zones.map((zone) => (
      <NoGoZone key={zone.id} zone={zone} layout={layout}/>
    ))}

    {layers.routes && approaching.map((robot) => (
      <ChargerApproach
        key={`approach-${robot.id}`} from={robot.pose}
        charger={chargingStation} layout={layout}
      />
    ))}
    {robots.map((robot) => <Amr
      key={robot.id} robot={robot}
      selected={selectedRobotId === robot.id} onSelect={onSelect} layout={layout}
    />)}

    <ContactShadows
      position={[0, 0.02, 0]} scale={[layout.width + 4, layout.height + 4]}
      opacity={0.42} blur={2.4} far={4} resolution={1024} color="#020a0e"
    />
  </Canvas>;
}
