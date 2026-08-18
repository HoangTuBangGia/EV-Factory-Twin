"use client";

import { ContactShadows, Grid, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { FACTORY_SIZE } from "@/lib/coordinate";
import { rectCenter, toScene, ZONE } from "@/lib/factory-layout";
import type { Robot } from "@/schemas/robot";
import { Amr } from "./amr";
import { BatteryBuffer } from "./battery-buffer";
import { ChargingStation } from "./charging-station";
import { MarriageStation } from "./marriage-station";
import { NoGoZone } from "./no-go-zone";
import { ChargerApproach, RouteLanes } from "./route-lanes";
import { BuildingShell, FloorLabel, PaintedRect } from "./shell";
import { concreteColorTexture, concreteRoughnessTexture, floorLabelTexture } from "./textures";

const { width: FACTORY_WIDTH, height: FACTORY_DEPTH } = FACTORY_SIZE;
const HOME_POSITION: [number, number, number] = [-3.2, 15.5, 19.5];

/** Sealed-concrete slab with a metre grid and 5 m section joints. */
function FactoryFloor() {
  const colorMap = useMemo(() => concreteColorTexture(), []);
  const roughnessMap = useMemo(() => concreteRoughnessTexture(), []);
  const idleLabel = useMemo(() => floorLabelTexture("IDLE / STAGING", "#8fa8b4"), []);
  const idleRect = ZONE.IDLE_ZONE;
  const idleCentre = rectCenter(idleRect);
  const [idleX, , idleZ] = toScene(idleCentre);

  return <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[FACTORY_WIDTH, FACTORY_DEPTH]}/>
      <meshStandardMaterial
        map={colorMap} roughnessMap={roughnessMap} color="#20343d"
        roughness={0.72} metalness={0.16}
      />
    </mesh>
    <Grid
      args={[FACTORY_WIDTH, FACTORY_DEPTH]} position={[0, 0.004, 0]}
      cellSize={1} cellThickness={0.5} cellColor="#1d3a45"
      sectionSize={5} sectionThickness={1.1} sectionColor="#2c5f6d"
      fadeDistance={58} fadeStrength={1.1} side={THREE.DoubleSide}
    />
    <group position={[idleX, 0, idleZ]}>
      <PaintedRect
        width={idleRect.x1 - idleRect.x0} depth={idleRect.y1 - idleRect.y0}
        color="#6b8794" fillOpacity={0.12} lineOpacity={0.5} height={0.008}
      />
      <FloorLabel texture={idleLabel} width={2.4} position={[0, 0.022, 0]} opacity={0.7}/>
    </group>
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
}

export function FactoryScene({
  robots, selectedRobotId, onSelect, bufferStock, resetSignal,
}: FactorySceneProps) {
  const chargingCount = robots.filter((robot) => robot.status === "CHARGING").length;
  const joining = robots.some((robot) => robot.status === "DROPPING");
  const approaching = robots.filter((robot) => robot.status === "MOVING_TO_CHARGER");

  return <Canvas
    shadows="percentage" dpr={[1, 1.85]} camera={{ position: HOME_POSITION, fov: 40, near: 0.5, far: 140 }}
    gl={{ antialias: true, powerPreference: "high-performance" }}
    onPointerMissed={() => onSelect(null)}
  >
    <color attach="background" args={["#060f15"]}/>
    <fog attach="fog" args={["#060f15", 30, 74]}/>
    <Lighting/>
    <CameraRig resetSignal={resetSignal}/>

    <FactoryFloor/>
    <BuildingShell width={FACTORY_WIDTH} depth={FACTORY_DEPTH}/>
    <RouteLanes/>
    <BatteryBuffer stockLevel={bufferStock}/>
    <MarriageStation joining={joining}/>
    <ChargingStation occupied={chargingCount}/>
    <NoGoZone/>

    {approaching.map((robot) => <ChargerApproach key={`approach-${robot.id}`} from={robot.pose}/>)}
    {robots.map((robot) => <Amr
      key={robot.id} robot={robot}
      selected={selectedRobotId === robot.id} onSelect={onSelect}
    />)}

    <ContactShadows
      position={[0, 0.02, 0]} scale={[FACTORY_WIDTH + 4, FACTORY_DEPTH + 4]}
      opacity={0.42} blur={2.4} far={4} resolution={1024} color="#020a0e"
    />
  </Canvas>;
}
