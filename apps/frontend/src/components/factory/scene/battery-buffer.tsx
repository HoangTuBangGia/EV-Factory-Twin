"use client";

import { useMemo } from "react";
import { BUFFER_SLOT_COUNT, toScene } from "@/lib/factory-layout";
import type { FactoryLayout, FactoryStation } from "@/schemas/factory";
import { Bollard, FloorLabel, PaintedRect } from "./shell";
import { floorLabelTexture, hazardStripeTexture, hmiPanelTexture } from "./textures";

const RACK_COLUMNS = [-1.15, 0, 1.15];
const RACK_LEVELS = [0.58, 1.4];

/** A charged pack: dark case, cyan cell-stack trim and a state-of-charge pip row. */
function BatteryPack({ position }: { position: [number, number, number] }) {
  return <group position={position}>
    <mesh castShadow receiveShadow>
      <boxGeometry args={[1.0, 0.24, 0.68]}/>
      <meshStandardMaterial color="#1d2f38" roughness={0.44} metalness={0.62}/>
    </mesh>
    <mesh position={[0, 0.14, 0]}>
      <boxGeometry args={[0.86, 0.05, 0.56]}/>
      <meshStandardMaterial color="#24404a" roughness={0.35} metalness={0.7}/>
    </mesh>
    {[-1, 1].map((side) =>
      <mesh key={side} position={[0, 0.02, side * 0.345]}>
        <boxGeometry args={[0.9, 0.05, 0.012]}/>
        <meshStandardMaterial color="#3fe6d0" emissive="#2dd4bf" emissiveIntensity={1.1} toneMapped={false}/>
      </mesh>)}
    {[-0.3, -0.1, 0.1, 0.3].map((x) =>
      <mesh key={x} position={[x, 0.17, 0.2]}>
        <boxGeometry args={[0.07, 0.012, 0.07]}/>
        <meshStandardMaterial color="#8ef7e6" emissive="#3fe6d0" emissiveIntensity={1.4} toneMapped={false}/>
      </mesh>)}
  </group>;
}

/** Empty shelf position: just the roller bed, so buffer level reads at a glance. */
function EmptySlot({ position }: { position: [number, number, number] }) {
  return <group position={position}>
    {[-0.22, 0, 0.22].map((z) =>
      <mesh key={z} position={[0, 0, z]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.03, 0.03, 0.94, 8]}/>
        <meshStandardMaterial color="#22343d" roughness={0.5} metalness={0.6}/>
      </mesh>)}
  </group>;
}

/**
 * Battery Buffer: a two-level pallet rack of charged packs beside the pickup
 * pad. Occupied slot count tracks the simulator's queued task depth.
 */
export function BatteryBuffer({ stockLevel, station, layout }: {
  stockLevel: number;
  station: FactoryStation;
  layout: FactoryLayout;
}) {
  const centre = { x: station.x + 0.6, y: station.y };
  const width = 4, depth = 4;
  const [cx, , cz] = toScene(centre, layout);

  const label = useMemo(() => floorLabelTexture("BATTERY BUFFER", "#7ecbdc", "CHARGED PACK STORE"), []);
  const hazard = useMemo(() => {
    const texture = hazardStripeTexture();
    texture.repeat.set(3, 3);
    return texture;
  }, []);
  const panel = useMemo(() => hmiPanelTexture("BUFFER", ["RACK B-01", "PICK FACE 1", "AUTO"], "#3fe6d0"), []);

  // Pickup pad sits exactly on the station anchor the router drives AMRs to.
  const padX = station.x - centre.x, padZ = -(station.y - centre.y);
  const rackZ = -1.35;
  const filled = Math.max(0, Math.min(BUFFER_SLOT_COUNT, Math.round(stockLevel)));

  return <group position={[cx, 0, cz]}>
    <PaintedRect width={width} depth={depth} color="#2f7d8f" fillOpacity={0.2} height={0.008}/>
    <FloorLabel texture={label} width={width * 0.82} position={[0, 0.022, depth * 0.3]}/>

    <group position={[padX, 0, padZ]}>
      <mesh position={[0, 0.018, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.5, 1.5]}/>
        <meshStandardMaterial map={hazard} transparent opacity={0.4} roughness={0.9} depthWrite={false}/>
      </mesh>
      <mesh position={[0, 0.024, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.74, 0.8, 40]}/>
        <meshBasicMaterial color="#3fe6d0" transparent opacity={0.6} depthWrite={false}/>
      </mesh>
    </group>

    <group position={[0, 0, rackZ]}>
      {[-1.68, 1.68].flatMap((x) => [-0.42, 0.42].map((z) =>
        <mesh key={`${x}:${z}`} position={[x, 1.15, z]} castShadow>
          <boxGeometry args={[0.1, 2.3, 0.1]}/>
          <meshStandardMaterial color="#2b4956" roughness={0.5} metalness={0.68}/>
        </mesh>))}
      {[0.3, ...RACK_LEVELS.map((y) => y - 0.16), 2.24].map((y) => <group key={y}>
        {[-0.42, 0.42].map((z) =>
          <mesh key={z} position={[0, y, z]} castShadow>
            <boxGeometry args={[3.44, 0.09, 0.11]}/>
            <meshStandardMaterial color="#315563" roughness={0.48} metalness={0.7}/>
          </mesh>)}
      </group>)}
      {[-1.68, 1.68].map((x) =>
        <mesh key={x} position={[x, 1.3, 0]} rotation={[0.72, 0, 0]}>
          <boxGeometry args={[0.05, 1.9, 0.05]}/>
          <meshStandardMaterial color="#294653" roughness={0.55} metalness={0.6}/>
        </mesh>)}
      {RACK_LEVELS.flatMap((y, level) => RACK_COLUMNS.map((x, column) => {
        const index = level * RACK_COLUMNS.length + column;
        return index < filled
          ? <BatteryPack key={`p${index}`} position={[x, y, 0]}/>
          : <EmptySlot key={`e${index}`} position={[x, y - 0.09, 0]}/>;
      }))}
      <mesh position={[0, 2.52, 0]}>
        <boxGeometry args={[2.1, 0.34, 0.06]}/>
        <meshStandardMaterial color="#0d1b22" roughness={0.6}/>
      </mesh>
      <mesh position={[0, 2.52, -0.035]}>
        <planeGeometry args={[1.9, 0.26]}/>
        <meshStandardMaterial color="#0a161c" emissive="#2dd4bf" emissiveIntensity={0.32}/>
      </mesh>
    </group>

    {/* South of the aisle: the lane spans world y 3.1-4.9 here, so nothing may
        stand between the pickup pad and the rack. */}
    <group position={[-0.4, 0, 1.4]} rotation={[0, 0.35, 0]}>
      <mesh position={[0, 0.62, 0]} castShadow>
        <boxGeometry args={[0.07, 1.24, 0.07]}/>
        <meshStandardMaterial color="#243c47" roughness={0.6} metalness={0.5}/>
      </mesh>
      <mesh position={[0, 1.34, 0]} rotation={[-0.32, 0, 0]} castShadow>
        <boxGeometry args={[0.62, 0.42, 0.05]}/>
        <meshStandardMaterial color="#0c1a21" roughness={0.5}/>
      </mesh>
      <mesh position={[0, 1.34, 0.028]} rotation={[-0.32, 0, 0]}>
        <planeGeometry args={[0.56, 0.36]}/>
        <meshStandardMaterial map={panel} emissiveMap={panel} emissive="#ffffff" emissiveIntensity={0.5} toneMapped={false}/>
      </mesh>
    </group>

    <Bollard position={[-1.95, 0, rackZ]}/>
    <Bollard position={[1.95, 0, rackZ]}/>
  </group>;
}
