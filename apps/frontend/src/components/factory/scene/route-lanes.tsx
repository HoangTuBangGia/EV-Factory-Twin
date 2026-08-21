"use client";

import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { Line2 } from "three-stdlib";
import { LANE_WIDTH, toScene } from "@/lib/factory-layout";
import type { FactoryLayout, FactoryRoute, WorldPoint } from "@/schemas/factory";
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
    for (const route of routes) {
      for (let i = 0; i < route.waypoints.length - 1; i += 1) {
        const [ax, , az] = toScene(route.waypoints[i], layout);
        const [bx, , bz] = toScene(route.waypoints[i + 1], layout);
        const dx = bx - ax, dz = bz - az;
        const length = Math.hypot(dx, dz);
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

/**
 * The simulator sends a charging robot straight to the charger from wherever it
 * stands (CHARGER_ROUTE_KEY), so this corridor is drawn live per robot instead
 * of being painted on the slab.
 */
export function ChargerApproach({ from, charger, layout }: {
  from: WorldPoint;
  charger: WorldPoint;
  layout: FactoryLayout;
}) {
  const line = useRef<Line2>(null);
  const target = useRef(from);
  target.current = from;
  const drawn = useRef({ x: Number.NaN, y: Number.NaN });

  // Held stable so drei keeps one LineGeometry for the corridor's lifetime; the
  // endpoints are rewritten in place whenever a new pose actually arrives.
  const points = useMemo(() => [new THREE.Vector3(), new THREE.Vector3()], []);

  useFrame((_, delta) => {
    const object = line.current;
    if (!object) return;
    const pose = target.current;
    if (pose.x !== drawn.current.x || pose.y !== drawn.current.y) {
      const [ax, , az] = toScene(pose, layout, 0.06);
      const [bx, , bz] = toScene(charger, layout, 0.06);
      object.geometry.setPositions([ax, 0.06, az, bx, 0.06, bz]);
      object.computeLineDistances();
      drawn.current = { x: pose.x, y: pose.y };
    }
    object.material.dashOffset -= delta * 0.45;
  });

  return <Line
    ref={line} points={points} color="#fbbf24" lineWidth={2}
    dashed dashSize={0.32} gapSize={0.22} transparent opacity={0.7}
  />;
}
