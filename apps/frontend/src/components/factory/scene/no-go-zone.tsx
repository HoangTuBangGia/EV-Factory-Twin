"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { boundsForPoints, rectCenter, rectSize, toScene } from "@/lib/factory-layout";
import type { FactoryLayout, NoGoZone as NoGoZoneData } from "@/schemas/factory";
import { Bollard, FloorLabel, PaintedRect } from "./shell";
import { floorLabelTexture, hazardStripeTexture, warningSignTexture } from "./textures";

/** Translucent light curtain: reads as a volume the fleet must not enter. */
let curtainMaterial: THREE.MeshBasicMaterial | null = null;

/** All four walls share one gradient, so the curtain costs a single texture. */
function keepOutMaterial() {
  if (curtainMaterial) return curtainMaterial;
  const canvas = document.createElement("canvas");
  canvas.width = 4; canvas.height = 64;
  const context = canvas.getContext("2d");
  if (context) {
    const gradient = context.createLinearGradient(0, 64, 0, 0);
    gradient.addColorStop(0, "rgba(251,113,133,0.5)");
    gradient.addColorStop(0.45, "rgba(251,113,133,0.16)");
    gradient.addColorStop(1, "rgba(251,113,133,0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 4, 64);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  curtainMaterial = new THREE.MeshBasicMaterial({
    map: texture, transparent: true, depthWrite: false,
    side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
  });
  return curtainMaterial;
}

function KeepOutWall({ width, height, position, rotation }: {
  width: number; height: number; position: [number, number, number]; rotation: [number, number, number];
}) {
  const material = useMemo(keepOutMaterial, []);

  return <mesh position={position} rotation={rotation} material={material}>
    <planeGeometry args={[width, height]}/>
  </mesh>;
}

/**
 * No-go zone: a hazard-painted exclusion patch fenced by bollards and rails,
 * with a light curtain and a sweeping safety scanner so it reads as active.
 */
export function NoGoZone({ zone, layout }: {
  zone: NoGoZoneData;
  layout: FactoryLayout;
}) {
  const rect = boundsForPoints(zone.points);
  const centre = rectCenter(rect);
  const { width, depth } = rectSize(rect);
  const [cx, , cz] = toScene(centre, layout);
  const halfWidth = width / 2, halfDepth = depth / 2;

  const stripes = useMemo(() => {
    const texture = hazardStripeTexture("#f4c236", "#1a1206");
    texture.repeat.set(width / 1.1, depth / 1.1);
    return texture;
  }, [width, depth]);
  const label = useMemo(() => floorLabelTexture("NO-GO ZONE", "#ff9bac", "KEEP FLEET CLEAR"), []);
  const sign = useMemo(() => warningSignTexture(), []);

  const scanner = useRef<THREE.Mesh>(null);
  const scannerMaterial = useRef<THREE.MeshBasicMaterial>(null);

  useFrame((state) => {
    const cycle = (state.clock.elapsedTime * 0.42) % 1;
    if (scanner.current) scanner.current.position.x = -halfWidth + cycle * width;
    if (scannerMaterial.current) scannerMaterial.current.opacity = 0.16 + Math.sin(cycle * Math.PI) * 0.44;
  });

  return <group position={[cx, 0, cz]}>
    <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[width, depth]}/>
      <meshStandardMaterial map={stripes} roughness={0.88} metalness={0.05} transparent opacity={0.55}/>
    </mesh>
    <PaintedRect width={width} depth={depth} color="#fb7185" fillOpacity={0.12} lineWidth={0.1} lineOpacity={0.9} height={0.016}/>
    <FloorLabel texture={label} width={width * 0.7} position={[0, 0.026, 0]} opacity={0.95}/>

    <mesh ref={scanner} position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[0.16, depth]}/>
      <meshBasicMaterial ref={scannerMaterial} color="#ff9bac" transparent opacity={0.3} depthWrite={false}/>
    </mesh>

    {([[-1, -1], [1, -1], [-1, 1], [1, 1]] as const).map(([sx, sz], index) =>
      <Bollard key={index} position={[sx * halfWidth, 0, sz * halfDepth]} height={0.95} color="#fb7185"/>)}
    {[0.42, 0.78].map((y) => <group key={y}>
      {[-1, 1].map((sz) =>
        <mesh key={`x${sz}`} position={[0, y, sz * halfDepth]}>
          <cylinderGeometry args={[0.022, 0.022, width, 8]}/>
          <meshStandardMaterial color="#c4566a" roughness={0.6} metalness={0.4}/>
        </mesh>)}
      {[-1, 1].map((sx) =>
        <mesh key={`z${sx}`} position={[sx * halfWidth, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.022, 0.022, depth, 8]}/>
          <meshStandardMaterial color="#c4566a" roughness={0.6} metalness={0.4}/>
        </mesh>)}
    </group>)}
    {[-1, 1].map((sz) =>
      <KeepOutWall key={`kx${sz}`} width={width} height={0.95} position={[0, 0.475, sz * halfDepth]} rotation={[0, 0, 0]}/>)}
    {[-1, 1].map((sx) =>
      <KeepOutWall key={`kz${sx}`} width={depth} height={0.95} position={[sx * halfWidth, 0.475, 0]} rotation={[0, Math.PI / 2, 0]}/>)}

    <group position={[-halfWidth + 0.1, 0, halfDepth + 0.24]}>
      <mesh position={[0, 0.6, 0]} castShadow>
        <cylinderGeometry args={[0.045, 0.045, 1.2, 10]}/>
        <meshStandardMaterial color="#26404a" roughness={0.6} metalness={0.5}/>
      </mesh>
      <mesh position={[0, 1.34, 0.01]}>
        <planeGeometry args={[0.46, 0.46]}/>
        <meshBasicMaterial map={sign} transparent side={THREE.DoubleSide}/>
      </mesh>
    </group>
    <pointLight position={[0, 1.1, 0]} intensity={3.2} distance={5.5} decay={2} color="#fb7185"/>
  </group>;
}
