"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { LANE_WIDTH, toScene } from "@/lib/factory-layout";
import type { FactoryLayout, FactoryRoute } from "@/schemas/factory";
import { laneChevronTexture } from "./textures";

interface Segment {
  mid: [number, number, number];
  length: number;
  angle: number;
  chevrons: THREE.Texture;
}

/**
 * Drivable aisles derived from the active layout so painted lanes and AMR poses
 * use the same coordinate system. Chevrons show flow direction.
 */
export function RouteLanes({ routes, layout }: {
  routes: FactoryRoute[];
  layout: FactoryLayout;
}) {
  const segments = useMemo<Segment[]>(() => {
    const base = laneChevronTexture();
    const built: Segment[] = [];
    const seen = new Set<string>();
    for (const route of routes) {
      for (let i = 0; i < route.waypoints.length - 1; i += 1) {
        const [ax, , az] = toScene(route.waypoints[i], layout);
        const [bx, , bz] = toScene(route.waypoints[i + 1], layout);
        const dx = bx - ax, dz = bz - az;
        const length = Math.hypot(dx, dz);
        const key = [`${ax}:${az}`, `${bx}:${bz}`].sort().join("|");
        if (seen.has(key)) continue;
        seen.add(key);
        const chevrons = base.clone();
        chevrons.needsUpdate = true;
        chevrons.repeat.set(length / 1.5, 1);
        built.push({
          mid: [(ax + bx) / 2, 0, (az + bz) / 2],
          length,
          angle: Math.atan2(-dz, dx),
          chevrons,
        });
      }
    }
    return built;
  }, [layout, routes]);

  useFrame((_, delta) => {
    for (const segment of segments) {
      segment.chevrons.offset.x = (segment.chevrons.offset.x - delta * 0.26) % 1;
    }
  });

  return <group>
    {segments.map((segment, index) => <group key={`seg${index}`} position={segment.mid} rotation={[0, segment.angle, 0]}>
      <mesh position={[0, 0.006, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[segment.length, LANE_WIDTH]}/>
        <meshStandardMaterial color="#132630" roughness={0.78} metalness={0.1} transparent opacity={0.95} depthWrite={false}/>
      </mesh>
      {[-1, 1].map((side) =>
        <mesh key={side} position={[0, 0.012, side * (LANE_WIDTH / 2 - 0.06)]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[segment.length, 0.075]}/>
          <meshBasicMaterial color="#7fe9dc" transparent opacity={0.5} depthWrite={false}/>
        </mesh>)}
      <mesh position={[0, 0.016, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[segment.length, 0.62]}/>
        <meshBasicMaterial map={segment.chevrons} transparent opacity={0.55} depthWrite={false}/>
      </mesh>
    </group>)}

    {routes.flatMap((route) => route.waypoints.slice(1, -1).map((joint, index) => {
      const [x, , z] = toScene(joint, layout);
      return <group key={`${route.id}-joint${index}`} position={[x, 0, z]}>
        <mesh position={[0, 0.007, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[LANE_WIDTH / 2, 28]}/>
          <meshStandardMaterial color="#132630" roughness={0.78} metalness={0.1} transparent opacity={0.95} depthWrite={false}/>
        </mesh>
        <mesh position={[0, 0.013, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[LANE_WIDTH / 2 - 0.09, LANE_WIDTH / 2 - 0.02, 32]}/>
          <meshBasicMaterial color="#7fe9dc" transparent opacity={0.35} depthWrite={false}/>
        </mesh>
        <mesh position={[0, 0.015, 0]} rotation={[-Math.PI / 2, 0, Math.PI / 4]}>
          <ringGeometry args={[0.15, 0.23, 4]}/>
          <meshBasicMaterial color="#f4c236" transparent opacity={0.55} depthWrite={false}/>
        </mesh>
      </group>;
    }))}
  </group>;
}
