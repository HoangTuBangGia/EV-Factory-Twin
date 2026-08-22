"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { CHARGER_BAY_COUNT, toScene } from "@/lib/factory-layout";
import type { FactoryLayout, FactoryStation } from "@/schemas/factory";
import { FloorLabel, PaintedRect } from "./shell";
import { floorLabelTexture, hmiPanelTexture } from "./textures";

const BAY_X = [-0.95, 0, 0.95];
const CABINET_Z = -1.28;
// Constant per bay, so the cable geometry is built once instead of per frame.
const CABLE_FROM: [number, number, number] = [0.18, 1.42, CABINET_Z + 0.2];
const CABLE_TO: [number, number, number] = [0.02, 0.1, -0.42];

/** Slack charging lead, drawn as a catenary tube from cabinet to floor puck. */
function ChargeCable({ from, to, active }: {
  from: [number, number, number]; to: [number, number, number]; active: boolean;
}) {
  const geometry = useMemo(() => {
    const start = new THREE.Vector3(...from);
    const end = new THREE.Vector3(...to);
    const sag = start.distanceTo(end) * 0.42;
    const curve = new THREE.CatmullRomCurve3([
      start,
      start.clone().lerp(end, 0.3).setY(start.y - sag * 0.7),
      start.clone().lerp(end, 0.68).setY(Math.min(start.y, end.y) - sag * 0.15 + 0.12),
      end,
    ]);
    return new THREE.TubeGeometry(curve, 26, 0.028, 8, false);
  }, [from, to]);
  useEffect(() => () => geometry.dispose(), [geometry]);

  return <mesh geometry={geometry} castShadow>
    <meshStandardMaterial
      color={active ? "#1f3f3c" : "#141d21"} roughness={0.75} metalness={0.2}
      emissive={active ? "#2dd4bf" : "#000000"} emissiveIntensity={active ? 0.35 : 0}
    />
  </mesh>;
}

/** DC fast-charge cabinet with an HMI face and a state LED column. */
function ChargerCabinet({ position, bay, active }: {
  position: [number, number, number]; bay: number; active: boolean;
}) {
  const led = useRef<THREE.MeshStandardMaterial>(null);
  const panel = useMemo(
    () => hmiPanelTexture(`BAY 0${bay}`, active ? ["DC CHARGE", "350 A", "LOCKED"] : ["READY", "IDLE", "UNLOCKED"],
      active ? "#fbbf24" : "#3fe6d0"),
    [bay, active],
  );
  useEffect(() => () => panel.dispose(), [panel]);

  useFrame((state) => {
    if (!led.current) return;
    led.current.emissiveIntensity = active
      ? 1.1 + Math.sin(state.clock.elapsedTime * 3.4 + bay) * 0.55
      : 0.4;
  });

  return <group position={position}>
    <mesh position={[0, 0.03, 0]} castShadow receiveShadow>
      <boxGeometry args={[0.72, 0.06, 0.56]}/>
      <meshStandardMaterial color="#16252c" roughness={0.65} metalness={0.4}/>
    </mesh>
    <mesh position={[0, 0.82, 0]} castShadow receiveShadow>
      <boxGeometry args={[0.62, 1.52, 0.44]}/>
      <meshStandardMaterial color="#1a2e37" roughness={0.42} metalness={0.66}/>
    </mesh>
    <mesh position={[0, 1.6, 0]} castShadow>
      <boxGeometry args={[0.68, 0.08, 0.5]}/>
      <meshStandardMaterial color="#223c47" roughness={0.4} metalness={0.7}/>
    </mesh>
    <mesh position={[0, 1.06, 0.226]}>
      <planeGeometry args={[0.46, 0.32]}/>
      <meshStandardMaterial map={panel} emissiveMap={panel} emissive="#ffffff" emissiveIntensity={0.55} toneMapped={false}/>
    </mesh>
    <mesh position={[0, 0.52, 0.226]}>
      <boxGeometry args={[0.08, 0.44, 0.014]}/>
      <meshStandardMaterial
        ref={led} color={active ? "#fbbf24" : "#3fe6d0"}
        emissive={active ? "#fbbf24" : "#2dd4bf"} emissiveIntensity={0.4} toneMapped={false}
      />
    </mesh>
    {/* Always mounted: adding or removing a light changes three's light count
        and forces every material in the scene to recompile. */}
    <pointLight position={[0, 0.7, 0.5]} intensity={active ? 2.6 : 0} distance={2.6} decay={2} color="#fbbf24"/>
  </group>;
}

/**
 * Charging Station: three DC bays with wheel stops, hanging leads and live
 * occupancy driven by how many AMRs currently report CHARGING.
 */
export function ChargingStation({ occupied, station, layout }: {
  occupied: number;
  station: FactoryStation;
  layout: FactoryLayout;
}) {
  const centre = { x: station.x + 0.3, y: station.y + 0.1 };
  const width = 3.4, depth = 3.4;
  const [cx, , cz] = toScene(centre, layout);
  const label = useMemo(() => floorLabelTexture("CHARGING", "#7fe0c4", "DC FAST BAYS"), []);
  const busy = Math.max(0, Math.min(CHARGER_BAY_COUNT, Math.round(occupied)));

  // Every charging AMR parks on CHARGING_STATION exactly, so the bay row is
  // centred on that anchor rather than on the painted rectangle — otherwise a
  // docked robot straddles two bays.
  const dockX = station.x - centre.x, dockZ = -(station.y - centre.y);

  return <group position={[cx, 0, cz]}>
    <PaintedRect width={width} depth={depth} color="#2f8f7a" fillOpacity={0.2} height={0.008}/>
    <FloorLabel texture={label} width={width * 0.72} position={[0, 0.022, depth * 0.36]}/>

    <group position={[dockX, 0, dockZ]}>
      {BAY_X.map((x, index) => {
        const active = index < busy;
        return <group key={x} position={[x, 0, 0]}>
          <mesh position={[0, 0.016, -0.25]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[0.9, 1.7]}/>
            <meshStandardMaterial
              color={active ? "#2a4a3f" : "#14262c"} roughness={0.85}
              emissive={active ? "#1c6b58" : "#000000"} emissiveIntensity={active ? 0.5 : 0}
              transparent opacity={0.85} depthWrite={false}
            />
          </mesh>
          {[-1, 1].map((side) =>
            <mesh key={side} position={[side * 0.44, 0.02, -0.25]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[0.055, 1.7]}/>
              <meshBasicMaterial color={active ? "#fbbf24" : "#4fd6bd"} transparent opacity={0.7} depthWrite={false}/>
            </mesh>)}
          <mesh position={[0, 0.05, -0.98]} castShadow>
            <boxGeometry args={[0.78, 0.1, 0.1]}/>
            <meshStandardMaterial color="#f4c236" roughness={0.6} metalness={0.2}/>
          </mesh>
          <mesh position={[0, 0.04, -0.42]}>
            <cylinderGeometry args={[0.1, 0.12, 0.08, 14]}/>
            <meshStandardMaterial
              color="#22343d" roughness={0.5} metalness={0.6}
              emissive={active ? "#2dd4bf" : "#000000"} emissiveIntensity={active ? 0.8 : 0}
            />
          </mesh>
          <ChargerCabinet position={[0, 0, CABINET_Z]} bay={index + 1} active={active}/>
          <ChargeCable from={CABLE_FROM} to={CABLE_TO} active={active}/>
        </group>;
      })}

      <mesh position={[0, 2.0, CABINET_Z - 0.05]}>
        <boxGeometry args={[2.8, 0.16, 0.22]}/>
        <meshStandardMaterial color="#1d3540" roughness={0.6} metalness={0.45}/>
      </mesh>
      {BAY_X.map((x) =>
        <mesh key={`riser${x}`} position={[x, 1.8, CABINET_Z - 0.05]}>
          <cylinderGeometry args={[0.035, 0.035, 0.4, 8]}/>
          <meshStandardMaterial color="#243c47" roughness={0.6} metalness={0.5}/>
        </mesh>)}
    </group>
  </group>;
}
