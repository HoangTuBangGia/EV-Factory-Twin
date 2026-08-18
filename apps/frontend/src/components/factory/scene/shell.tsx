"use client";

import { useMemo } from "react";
import * as THREE from "three";

/** Thin painted floor rectangle: fill plus a stroked outline with corner ticks. */
export function PaintedRect({
  width, depth, color, fillOpacity = 0.34, lineWidth = 0.07,
  lineOpacity = 0.85, ticks = true, height = 0,
}: {
  width: number; depth: number; color: string; fillOpacity?: number;
  lineWidth?: number; lineOpacity?: number; ticks?: boolean; height?: number;
}) {
  const halfWidth = width / 2, halfDepth = depth / 2, tick = Math.min(width, depth) * 0.22;
  return <group position={[0, height, 0]}>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[width, depth]}/>
      <meshStandardMaterial color={color} transparent opacity={fillOpacity} roughness={0.85} metalness={0.05} depthWrite={false}/>
    </mesh>
    {([[0, -halfDepth], [0, halfDepth]] as const).map(([x, z], index) =>
      <mesh key={`h${index}`} position={[x, 0.004, z]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[width, lineWidth]}/>
        <meshBasicMaterial color={color} transparent opacity={lineOpacity} depthWrite={false}/>
      </mesh>)}
    {([[-halfWidth, 0], [halfWidth, 0]] as const).map(([x, z], index) =>
      <mesh key={`v${index}`} position={[x, 0.004, z]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[lineWidth, depth]}/>
        <meshBasicMaterial color={color} transparent opacity={lineOpacity} depthWrite={false}/>
      </mesh>)}
    {ticks && ([[-1, -1], [1, -1], [-1, 1], [1, 1]] as const).map(([sx, sz], index) => <group key={`t${index}`}>
      <mesh position={[sx * (halfWidth - tick / 2), 0.008, sz * (halfDepth - lineWidth * 2.4)]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[tick, lineWidth * 1.5]}/>
        <meshBasicMaterial color={color} transparent opacity={lineOpacity} depthWrite={false}/>
      </mesh>
      <mesh position={[sx * (halfWidth - lineWidth * 2.4), 0.008, sz * (halfDepth - tick / 2)]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[lineWidth * 1.5, tick]}/>
        <meshBasicMaterial color={color} transparent opacity={lineOpacity} depthWrite={false}/>
      </mesh>
    </group>)}
  </group>;
}

/** Floor-stencilled area name, laid flat on the slab. */
export function FloorLabel({
  texture, width, position, opacity = 0.9,
}: { texture: THREE.Texture; width: number; position: [number, number, number]; opacity?: number }) {
  return <mesh position={position} rotation={[-Math.PI / 2, 0, 0]}>
    <planeGeometry args={[width, width / 4]}/>
    <meshBasicMaterial map={texture} transparent opacity={opacity} depthWrite={false}/>
  </mesh>;
}

/** Reflective-banded safety bollard used at rack corners and keep-out edges. */
export function Bollard({ position, height = 0.72, color = "#f4c236" }: {
  position: [number, number, number]; height?: number; color?: string;
}) {
  return <group position={position}>
    <mesh position={[0, 0.02, 0]} castShadow receiveShadow>
      <cylinderGeometry args={[0.16, 0.18, 0.04, 16]}/>
      <meshStandardMaterial color="#16232a" roughness={0.7} metalness={0.4}/>
    </mesh>
    <mesh position={[0, height / 2, 0]} castShadow>
      <cylinderGeometry args={[0.075, 0.09, height, 14]}/>
      <meshStandardMaterial color={color} roughness={0.55} metalness={0.25}/>
    </mesh>
    {[height * 0.55, height * 0.82].map((y) =>
      <mesh key={y} position={[0, y, 0]}>
        <cylinderGeometry args={[0.083, 0.083, 0.07, 14]}/>
        <meshStandardMaterial color="#e9f6f8" emissive="#8fd6e0" emissiveIntensity={0.35} roughness={0.3}/>
      </mesh>)}
  </group>;
}

/** Perimeter curbs, corner columns, roof trusses and high-bay lamp fixtures. */
export function BuildingShell({ width, depth }: { width: number; depth: number }) {
  const halfWidth = width / 2, halfDepth = depth / 2;
  const curbHeight = 0.44, curbThickness = 0.26, columnHeight = 4.1, trussHeight = 3.75;

  const lampSpots = useMemo(() => {
    const spots: [number, number][] = [];
    for (const z of [-halfDepth * 0.52, halfDepth * 0.52]) {
      for (const x of [-halfWidth * 0.62, 0, halfWidth * 0.62]) spots.push([x, z]);
    }
    return spots;
  }, [halfWidth, halfDepth]);

  return <group>
    {([
      [0, -halfDepth - curbThickness / 2, width + curbThickness * 2, curbThickness],
      [0, halfDepth + curbThickness / 2, width + curbThickness * 2, curbThickness],
    ] as const).map(([x, z, w, d], index) => <group key={`cz${index}`}>
      <mesh position={[x, curbHeight / 2, z]} castShadow receiveShadow>
        <boxGeometry args={[w, curbHeight, d]}/>
        <meshStandardMaterial color="#152530" roughness={0.72} metalness={0.28}/>
      </mesh>
      <mesh position={[x, curbHeight + 0.012, z]}>
        <boxGeometry args={[w, 0.024, d * 0.72]}/>
        <meshStandardMaterial color="#f4c236" emissive="#8a6a12" emissiveIntensity={0.35} roughness={0.6}/>
      </mesh>
    </group>)}
    {([
      [-halfWidth - curbThickness / 2, 0, curbThickness, depth],
      [halfWidth + curbThickness / 2, 0, curbThickness, depth],
    ] as const).map(([x, z, w, d], index) => <group key={`cx${index}`}>
      <mesh position={[x, curbHeight / 2, z]} castShadow receiveShadow>
        <boxGeometry args={[w, curbHeight, d]}/>
        <meshStandardMaterial color="#152530" roughness={0.72} metalness={0.28}/>
      </mesh>
      <mesh position={[x, curbHeight + 0.012, z]}>
        <boxGeometry args={[w * 0.72, 0.024, d]}/>
        <meshStandardMaterial color="#f4c236" emissive="#8a6a12" emissiveIntensity={0.35} roughness={0.6}/>
      </mesh>
    </group>)}

    {([[-1, -1], [1, -1], [-1, 1], [1, 1]] as const).map(([sx, sz], index) =>
      <mesh key={`col${index}`} position={[sx * (halfWidth + 0.34), columnHeight / 2, sz * (halfDepth + 0.34)]} castShadow>
        <boxGeometry args={[0.46, columnHeight, 0.46]}/>
        <meshStandardMaterial color="#16262f" roughness={0.62} metalness={0.45}/>
      </mesh>)}

    {[-halfDepth * 0.55, 0, halfDepth * 0.55].map((z) => <group key={`truss${z}`} position={[0, trussHeight, z]}>
      {[0, 0.62].map((dy) =>
        <mesh key={dy} position={[0, dy, 0]}>
          <boxGeometry args={[width + 0.9, 0.09, 0.16]}/>
          <meshStandardMaterial color="#1b2e38" roughness={0.6} metalness={0.5}/>
        </mesh>)}
      {Array.from({ length: 13 }, (_, i) => -halfWidth + (i * width) / 12).map((x, i) =>
        <mesh key={x} position={[x, 0.31, 0]} rotation={[0, 0, i % 2 ? 0.62 : -0.62]}>
          <boxGeometry args={[0.05, 0.78, 0.09]}/>
          <meshStandardMaterial color="#1b2e38" roughness={0.65} metalness={0.4}/>
        </mesh>)}
    </group>)}

    {lampSpots.map(([x, z], index) => <group key={`lamp${index}`} position={[x, 0, z]}>
      <mesh position={[0, trussHeight - 0.28, 0]}>
        <boxGeometry args={[0.04, 0.5, 0.04]}/>
        <meshStandardMaterial color="#22323a" roughness={0.7}/>
      </mesh>
      <mesh position={[0, trussHeight - 0.58, 0]}>
        <boxGeometry args={[1.15, 0.09, 0.3]}/>
        <meshStandardMaterial color="#233642" roughness={0.5} metalness={0.5}/>
      </mesh>
      <mesh position={[0, trussHeight - 0.64, 0]}>
        <boxGeometry args={[1.05, 0.03, 0.22]}/>
        <meshStandardMaterial color="#dff6fb" emissive="#bfeef8" emissiveIntensity={1.5} toneMapped={false}/>
      </mesh>
      <pointLight position={[0, trussHeight - 0.9, 0]} intensity={9} distance={11} decay={2} color="#bfe6f2"/>
    </group>)}
  </group>;
}
