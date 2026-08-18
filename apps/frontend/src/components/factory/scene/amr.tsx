"use client";

import { Html, Line, RoundedBox } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, type CSSProperties } from "react";
import * as THREE from "three";
import type { Line2 } from "three-stdlib";
import { toScene } from "@/lib/factory-layout";
import type { Robot, RobotStatus } from "@/schemas/robot";
import { radialGlowTexture } from "./textures";

const STATUS_COLOR: Record<RobotStatus, string> = {
  IDLE: "#3fe6d0",
  MOVING_TO_PICKUP: "#38bdf8",
  PICKING: "#7dd3fc",
  DELIVERING: "#38bdf8",
  DROPPING: "#7dd3fc",
  MOVING_TO_CHARGER: "#fbbf24",
  WAITING: "#fbbf24",
  CHARGING: "#fbbf24",
  ERROR: "#fb7185",
  OFFLINE: "#64748b",
};

const PULSING: ReadonlySet<RobotStatus> = new Set<RobotStatus>([
  "MOVING_TO_PICKUP", "DELIVERING", "MOVING_TO_CHARGER", "CHARGING", "ERROR",
]);

const TRAIL_LENGTH = 26;
const LOW_BATTERY = 20;

function shortestAngleTo(from: number, to: number) {
  return ((to - from + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
}

/** Spinning LiDAR head; the sweep plane makes the scan visible from above. */
function LidarTurret({ color }: { color: string }) {
  const sweep = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (sweep.current) sweep.current.rotation.y += delta * 5.5;
  });

  return <group position={[0.3, 0.4, 0]}>
    <mesh castShadow>
      <cylinderGeometry args={[0.07, 0.075, 0.07, 16]}/>
      <meshStandardMaterial color="#131f25" roughness={0.5} metalness={0.6}/>
    </mesh>
    <mesh position={[0, 0.055, 0]}>
      <cylinderGeometry args={[0.062, 0.062, 0.045, 16]}/>
      <meshStandardMaterial color="#0a1216" roughness={0.2} metalness={0.4} emissive={color} emissiveIntensity={0.3}/>
    </mesh>
    <mesh position={[0, 0.09, 0]}>
      <cylinderGeometry args={[0.072, 0.072, 0.022, 16]}/>
      <meshStandardMaterial color="#1b2b33" roughness={0.45} metalness={0.65}/>
    </mesh>
    <group ref={sweep} position={[0, 0.055, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.07, 0.44, 24, 1, 0, 0.85]}/>
        <meshBasicMaterial color={color} transparent opacity={0.14} side={THREE.DoubleSide} depthWrite={false}/>
      </mesh>
    </group>
  </group>;
}

/** The pack an AMR is carrying, only present while payload_id is set. */
function CarriedPack() {
  return <group position={[0, 0.42, 0]}>
    <mesh castShadow>
      <boxGeometry args={[0.66, 0.16, 0.46]}/>
      <meshStandardMaterial color="#1d2f38" roughness={0.44} metalness={0.62}/>
    </mesh>
    {[-1, 1].map((side) =>
      <mesh key={side} position={[0, 0, side * 0.235]}>
        <boxGeometry args={[0.58, 0.036, 0.01]}/>
        <meshStandardMaterial color="#3fe6d0" emissive="#2dd4bf" emissiveIntensity={1.2} toneMapped={false}/>
      </mesh>)}
  </group>;
}

/**
 * One AMR. Telemetry arrives as discrete pose samples, so position and yaw are
 * damped toward the latest sample each frame and the wheels are spun from the
 * reported linear velocity — that is what makes the fleet read as driving
 * rather than teleporting between updates.
 */
export function Amr({ robot, selected, onSelect }: {
  robot: Robot; selected: boolean; onSelect: (id: string) => void;
}) {
  const root = useRef<THREE.Group>(null);
  const body = useRef<THREE.Group>(null);
  const wheels = useRef<(THREE.Mesh | null)[]>([]);
  const ring = useRef<THREE.MeshStandardMaterial>(null);
  const halo = useRef<THREE.Mesh>(null);
  const trailLine = useRef<Line2>(null);
  const spawned = useRef(false);

  const glow = useMemo(() => radialGlowTexture("rgba(63,230,208,0.6)"), []);
  const lowBattery = robot.battery < LOW_BATTERY;
  const statusColor = robot.status === "IDLE" && lowBattery ? "#fbbf24" : STATUS_COLOR[robot.status];
  const pulsing = PULSING.has(robot.status) || lowBattery;

  // Fixed-length ring buffer seeded at the spawn pose, so the Line geometry is
  // allocated once and only its positions are rewritten per frame.
  const trail = useRef<THREE.Vector3[]>([]);
  const seedPoints = useMemo(() => {
    const [x, , z] = toScene(robot.pose);
    trail.current = Array.from({ length: TRAIL_LENGTH }, () => new THREE.Vector3(x, 0.05, z));
    return trail.current.map((point) => point.clone());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [robot.id]);

  useFrame((state, delta) => {
    const group = root.current;
    if (!group) return;
    const [tx, , tz] = toScene(robot.pose);

    if (!spawned.current) {
      group.position.set(tx, 0, tz);
      group.rotation.y = robot.pose.yaw;
      spawned.current = true;
    } else {
      const step = Math.min(1, delta * 6.5);
      group.position.x += (tx - group.position.x) * step;
      group.position.z += (tz - group.position.z) * step;
      group.rotation.y += shortestAngleTo(group.rotation.y, robot.pose.yaw) * Math.min(1, delta * 5);
    }

    const spin = delta * (robot.velocity.linear / 0.105);
    for (const wheel of wheels.current) if (wheel) wheel.rotation.x -= spin;

    if (ring.current) {
      ring.current.emissiveIntensity = pulsing
        ? 1.0 + Math.sin(state.clock.elapsedTime * 5.5) * 0.6
        : 0.85;
    }
    if (body.current) {
      // Suspension bob while driving; settles flat when parked.
      const moving = Math.abs(robot.velocity.linear) > 0.02;
      body.current.position.y = moving ? Math.sin(state.clock.elapsedTime * 11) * 0.006 : 0;
    }
    if (halo.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.06;
      halo.current.scale.set(scale, scale, scale);
    }

    const points = trail.current;
    const head = points[points.length - 1];
    if (Math.hypot(head.x - group.position.x, head.z - group.position.z) > 0.15) {
      const recycled = points.shift();
      if (recycled) {
        recycled.set(group.position.x, 0.05, group.position.z);
        points.push(recycled);
      }
      const geometry = trailLine.current?.geometry;
      if (geometry) {
        const flat: number[] = [];
        for (const point of points) flat.push(point.x, point.y, point.z);
        geometry.setPositions(flat);
      }
    }
  });

  const select = (event: { stopPropagation: () => void }) => {
    event.stopPropagation();
    onSelect(robot.id);
  };

  return <>
    <Line
      ref={trailLine} points={seedPoints} color={statusColor}
      lineWidth={1.6} transparent opacity={0.3}
    />
    <group ref={root} onClick={select} onPointerOver={() => { document.body.style.cursor = "pointer"; }} onPointerOut={() => { document.body.style.cursor = ""; }}>
      <mesh position={[0, 0.012, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.9, 1.9]}/>
        <meshBasicMaterial map={glow} color={statusColor} transparent opacity={selected ? 0.5 : 0.22} depthWrite={false}/>
      </mesh>
      {selected && <mesh ref={halo} position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.62, 0.72, 48]}/>
        <meshBasicMaterial color={statusColor} transparent opacity={0.85} depthWrite={false}/>
      </mesh>}

      <group ref={body}>
        <RoundedBox args={[1.0, 0.26, 0.72]} radius={0.06} smoothness={3} position={[0, 0.21, 0]} castShadow receiveShadow>
          <meshStandardMaterial color="#1d2d35" roughness={0.42} metalness={0.7}/>
        </RoundedBox>
        <mesh position={[0, 0.1, 0]} castShadow>
          <boxGeometry args={[0.86, 0.1, 0.6]}/>
          <meshStandardMaterial color="#0e171c" roughness={0.65} metalness={0.4}/>
        </mesh>
        <RoundedBox args={[0.9, 0.05, 0.62]} radius={0.02} smoothness={2} position={[0, 0.36, 0]} castShadow>
          <meshStandardMaterial color="#2a4855" roughness={0.35} metalness={0.72}/>
        </RoundedBox>
        <mesh position={[-0.04, 0.392, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.0, 0.11, 3]}/>
          <meshBasicMaterial color={statusColor} transparent opacity={0.9}/>
        </mesh>

        <mesh position={[0, 0.3, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.355, 0.022, 8, 40]}/>
          <meshStandardMaterial
            ref={ring} color={statusColor} emissive={statusColor}
            emissiveIntensity={0.85} toneMapped={false} roughness={0.3}
          />
        </mesh>

        <mesh position={[0.48, 0.24, 0]} castShadow>
          <boxGeometry args={[0.06, 0.14, 0.6]}/>
          <meshStandardMaterial color="#121c21" roughness={0.6} metalness={0.5}/>
        </mesh>
        {[-1, 1].map((side) =>
          <mesh key={`head${side}`} position={[0.512, 0.24, side * 0.2]}>
            <boxGeometry args={[0.014, 0.06, 0.14]}/>
            <meshStandardMaterial color="#eafcff" emissive="#cdefff" emissiveIntensity={1.6} toneMapped={false}/>
          </mesh>)}
        {[-1, 1].map((side) =>
          <mesh key={`tail${side}`} position={[-0.505, 0.24, side * 0.2]}>
            <boxGeometry args={[0.014, 0.05, 0.12]}/>
            <meshStandardMaterial color="#ff8fa3" emissive="#fb7185" emissiveIntensity={1.1} toneMapped={false}/>
          </mesh>)}

        <LidarTurret color={statusColor}/>
        {robot.payload_id && <CarriedPack/>}
      </group>

      {([[-1, -1], [1, -1], [-1, 1], [1, 1]] as const).map(([sx, sz], index) =>
        <mesh
          key={index} ref={(mesh) => { wheels.current[index] = mesh; }}
          position={[sx * 0.31, 0.105, sz * 0.36]} rotation={[0, 0, Math.PI / 2]} castShadow
        >
          <cylinderGeometry args={[0.105, 0.105, 0.075, 18]}/>
          <meshStandardMaterial color="#0c1317" roughness={0.9} metalness={0.1}/>
        </mesh>)}

      {/*
        Html only consumes the props it declares and spreads the remainder onto
        its backing <group>, where THREE receives them: a dashed name like
        aria-label is read as the pierced path group.aria.label and throws. DOM
        concerns therefore live on the child, which a native button also makes
        focusable and Enter/Space-activatable without hand-rolled key handling.
      */}
      <Html
        position={[0, 0.92, 0]} center distanceFactor={13} zIndexRange={[8, 0]}
        prepend occlude={false} pointerEvents="auto"
      >
        <button
          type="button"
          className={`robot-marker${lowBattery ? " low" : ""}${selected ? " selected" : ""}`}
          style={{ "--marker-accent": statusColor } as CSSProperties}
          aria-label={`${robot.id}, ${robot.status}, battery ${Math.round(robot.battery)} percent`}
          onClick={(event) => { event.stopPropagation(); onSelect(robot.id); }}
        >
          <span className="marker-id">{robot.id}</span>
          <span className="marker-meta">
            <i className="marker-dot"/>{Math.round(robot.battery)}%
          </span>
        </button>
      </Html>
    </group>
  </>;
}
