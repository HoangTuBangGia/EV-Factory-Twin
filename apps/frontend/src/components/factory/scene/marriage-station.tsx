"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { rectCenter, rectSize, toScene, ZONE } from "@/lib/factory-layout";
import { Bollard, FloorLabel, PaintedRect } from "./shell";
import { floorLabelTexture, hazardStripeTexture, hmiPanelTexture } from "./textures";

const BODY_X = 1.45;

/** Body-in-white on the line: floorpan, cabin, glazing and wheels from primitives. */
function VehicleBody() {
  return <group>
    <mesh position={[0, 0, 0]} castShadow receiveShadow>
      <boxGeometry args={[1.82, 0.16, 4.15]}/>
      <meshStandardMaterial color="#4d6b78" roughness={0.34} metalness={0.78}/>
    </mesh>
    <mesh position={[0, 0.1, 0]}>
      <boxGeometry args={[1.6, 0.04, 3.9]}/>
      <meshStandardMaterial color="#5b7c8a" roughness={0.28} metalness={0.85}/>
    </mesh>
    {[-1, 1].map((side) =>
      <mesh key={side} position={[side * 0.88, 0.34, 0]} castShadow>
        <boxGeometry args={[0.09, 0.56, 4.0]}/>
        <meshStandardMaterial color="#476474" roughness={0.36} metalness={0.8}/>
      </mesh>)}
    <mesh position={[0, 0.62, -0.15]} castShadow>
      <boxGeometry args={[1.72, 0.62, 2.05]}/>
      <meshStandardMaterial color="#43606f" roughness={0.38} metalness={0.76}/>
    </mesh>
    <mesh position={[0, 0.98, -0.15]} castShadow>
      <boxGeometry args={[1.5, 0.12, 1.85]}/>
      <meshStandardMaterial color="#3b5766" roughness={0.4} metalness={0.7}/>
    </mesh>
    {[[0, 0.68, -1.24, 0.42], [0, 0.68, 0.94, -0.42]].map(([x, y, z, tilt], index) =>
      <mesh key={index} position={[x, y, z]} rotation={[tilt, 0, 0]}>
        <planeGeometry args={[1.44, 0.78]}/>
        <meshPhysicalMaterial color="#8fd4e6" transparent opacity={0.26} roughness={0.08} metalness={0.1} side={THREE.DoubleSide}/>
      </mesh>)}
    {([[-1, -1], [1, -1], [-1, 1], [1, 1]] as const).map(([sx, sz], index) =>
      <mesh key={`w${index}`} position={[sx * 0.86, -0.18, sz * 1.42]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.33, 0.33, 0.2, 20]}/>
        <meshStandardMaterial color="#0e1519" roughness={0.88} metalness={0.15}/>
      </mesh>)}
    {[-1, 1].map((side) =>
      <mesh key={`l${side}`} position={[side * 0.6, 0.2, -2.06]}>
        <boxGeometry args={[0.42, 0.12, 0.05]}/>
        <meshStandardMaterial color="#e8fbff" emissive="#bfeef8" emissiveIntensity={1.2} toneMapped={false}/>
      </mesh>)}
  </group>;
}

/** Scissor table that lifts a pack from the AMR drop height into the pan. */
function ScissorLift({ raise }: { raise: number }) {
  const platform = useRef<THREE.Group>(null);
  const arms = useRef<(THREE.Mesh | null)[]>([]);
  const eased = useRef(0);

  useFrame((_, delta) => {
    eased.current = THREE.MathUtils.damp(eased.current, raise, 2.4, delta);
    const height = 0.18 + eased.current * 0.72;
    if (platform.current) platform.current.position.y = height;
    const angle = 0.3 + eased.current * 0.52;
    arms.current.forEach((arm, index) => {
      if (arm) arm.rotation.x = index % 2 ? -angle : angle;
    });
  });

  return <group>
    <mesh position={[0, 0.07, 0]} castShadow receiveShadow>
      <boxGeometry args={[1.3, 0.14, 1.0]}/>
      <meshStandardMaterial color="#1c2f38" roughness={0.55} metalness={0.62}/>
    </mesh>
    {[-1, 1].flatMap((side) => [0, 1].map((slot) => {
      const index = (side < 0 ? 0 : 2) + slot;
      return <mesh
        key={index} ref={(mesh) => { arms.current[index] = mesh; }}
        position={[side * 0.44, 0.4, 0]} castShadow
      >
        <boxGeometry args={[0.07, 0.06, 0.98]}/>
        <meshStandardMaterial color={slot ? "#335662" : "#3b6270"} roughness={0.42} metalness={0.75}/>
      </mesh>;
    }))}
    <group ref={platform} position={[0, 0.18, 0]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.36, 0.1, 1.04]}/>
        <meshStandardMaterial color="#28444f" roughness={0.42} metalness={0.7}/>
      </mesh>
      <mesh position={[0, 0.06, 0]}>
        <boxGeometry args={[1.24, 0.02, 0.94]}/>
        <meshStandardMaterial color="#f4c236" emissive="#7a5c10" emissiveIntensity={0.3} roughness={0.6}/>
      </mesh>
      <mesh position={[0, 0.19, 0]} castShadow>
        <boxGeometry args={[0.98, 0.22, 0.66]}/>
        <meshStandardMaterial color="#1d2f38" roughness={0.44} metalness={0.62}/>
      </mesh>
      {[-1, 1].map((side) =>
        <mesh key={side} position={[0, 0.19, side * 0.335]}>
          <boxGeometry args={[0.88, 0.05, 0.012]}/>
          <meshStandardMaterial color="#3fe6d0" emissive="#2dd4bf" emissiveIntensity={1.1} toneMapped={false}/>
        </mesh>)}
    </group>
  </group>;
}

/** Amber rotating beacon; spins continuously and brightens while a join is running. */
function Beacon({ active }: { active: boolean }) {
  const sweep = useRef<THREE.Group>(null);
  const lamp = useRef<THREE.MeshStandardMaterial>(null);

  useFrame((state, delta) => {
    if (sweep.current) sweep.current.rotation.y += delta * (active ? 7 : 2.2);
    if (lamp.current) {
      lamp.current.emissiveIntensity = active
        ? 1.5 + Math.sin(state.clock.elapsedTime * 8) * 0.7
        : 0.35;
    }
  });

  return <group>
    <mesh position={[0, 0.06, 0]}>
      <cylinderGeometry args={[0.1, 0.12, 0.12, 14]}/>
      <meshStandardMaterial color="#1a2c34" roughness={0.6} metalness={0.5}/>
    </mesh>
    <mesh position={[0, 0.22, 0]}>
      <cylinderGeometry args={[0.11, 0.11, 0.2, 16]}/>
      <meshStandardMaterial ref={lamp} color="#f8b84a" emissive="#fbbf24" emissiveIntensity={0.35} transparent opacity={0.85} toneMapped={false}/>
    </mesh>
    <group ref={sweep} position={[0, 0.22, 0]}>
      <mesh position={[0, 0, 0.16]}>
        <planeGeometry args={[0.06, 0.16]}/>
        <meshBasicMaterial color="#fde68a" transparent opacity={0.85} side={THREE.DoubleSide}/>
      </mesh>
    </group>
  </group>;
}

/**
 * Marriage Station: the AMR drop pad, a scissor table that raises the pack, and
 * the body-in-white waiting on the line under a service gantry.
 */
export function MarriageStation({ joining }: { joining: boolean }) {
  const rect = ZONE.MARRIAGE_STATION;
  const centre = rectCenter(rect);
  const { width, depth } = rectSize(rect);
  const [cx, , cz] = toScene(centre);

  const label = useMemo(() => floorLabelTexture("MARRIAGE STATION", "#8fb6f0", "PACK / BODY JOIN"), []);
  const hazard = useMemo(() => {
    const texture = hazardStripeTexture("#f4c236", "#151007");
    texture.repeat.set(4, 4);
    return texture;
  }, []);
  const panel = useMemo(() => hmiPanelTexture(
    joining ? "JOIN ACTIVE" : "STANDBY",
    ["STATION M-01", joining ? "TORQUE SEQ" : "AWAIT PACK", "INTERLOCK OK"],
    joining ? "#fbbf24" : "#7dd3fc",
  ), [joining]);
  useEffect(() => () => panel.dispose(), [panel]);

  const padX = 16 - centre.x, padZ = -(8 - centre.y);
  const gantryHeight = 3.05;

  return <group position={[cx, 0, cz]}>
    <PaintedRect width={width} depth={depth} color="#3f6ea8" fillOpacity={0.2} height={0.008}/>
    <FloorLabel texture={label} width={width * 0.78} position={[0, 0.022, depth * 0.36]}/>

    <group position={[padX, 0, padZ]}>
      <mesh position={[0, 0.018, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.6, 1.6]}/>
        <meshStandardMaterial map={hazard} transparent opacity={0.38} roughness={0.9} depthWrite={false}/>
      </mesh>
      <mesh position={[0, 0.024, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.78, 0.85, 40]}/>
        <meshBasicMaterial color="#7dd3fc" transparent opacity={0.6} depthWrite={false}/>
      </mesh>
    </group>

    <group position={[BODY_X - 0.75, 0, 0]}>
      <ScissorLift raise={joining ? 1 : 0}/>
    </group>

    <mesh position={[BODY_X, 0.014, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[2.3, 4.4]}/>
      <meshStandardMaterial color="#0a141a" roughness={0.9} transparent opacity={0.72} depthWrite={false}/>
    </mesh>
    {/* Skillet conveyor. Its deck top sits at 0.81, exactly where the body's
        wheels bottom out, so the shell rests on the line instead of floating. */}
    <group position={[BODY_X, 0, 0]}>
      {([-1, 1] as const).flatMap((sx) => ([-1, 1] as const).map((sz) =>
        <mesh key={`ped${sx}${sz}`} position={[sx * 0.92, 0.36, sz * 1.6]} castShadow receiveShadow>
          <boxGeometry args={[0.22, 0.72, 0.26]}/>
          <meshStandardMaterial color="#1b2f39" roughness={0.6} metalness={0.55}/>
        </mesh>))}
      <mesh position={[0, 0.765, 0]} castShadow receiveShadow>
        <boxGeometry args={[2.14, 0.09, 4.5]}/>
        <meshStandardMaterial color="#24404c" roughness={0.5} metalness={0.68}/>
      </mesh>
      {[-1, 1].map((side) =>
        <mesh key={`kerb${side}`} position={[side * 1.02, 0.83, 0]}>
          <boxGeometry args={[0.09, 0.05, 4.5]}/>
          <meshStandardMaterial color="#f4c236" emissive="#7a5c10" emissiveIntensity={0.3} roughness={0.6}/>
        </mesh>)}
    </group>
    <group position={[BODY_X, 1.32, 0]}>
      <VehicleBody/>
    </group>

    {[-1.85, 1.85].map((z) => <group key={z} position={[0, 0, z]}>
      {[BODY_X - 1.5, BODY_X + 1.5].map((x) =>
        <mesh key={x} position={[x, gantryHeight / 2, 0]} castShadow>
          <boxGeometry args={[0.16, gantryHeight, 0.16]}/>
          <meshStandardMaterial color="#2a4653" roughness={0.5} metalness={0.7}/>
        </mesh>)}
      <mesh position={[BODY_X, gantryHeight, 0]} castShadow>
        <boxGeometry args={[3.3, 0.18, 0.18]}/>
        <meshStandardMaterial color="#31586a" roughness={0.45} metalness={0.72}/>
      </mesh>
    </group>)}
    {[BODY_X - 1.5, BODY_X + 1.5].map((x) =>
      <mesh key={`rail${x}`} position={[x, gantryHeight - 0.02, 0]} castShadow>
        <boxGeometry args={[0.13, 0.13, 3.9]}/>
        <meshStandardMaterial color="#2c4d5c" roughness={0.45} metalness={0.72}/>
      </mesh>)}
    <mesh position={[BODY_X, gantryHeight - 0.24, 0]}>
      <boxGeometry args={[0.5, 0.14, 3.6]}/>
      <meshStandardMaterial color="#1d3540" roughness={0.6} metalness={0.4}/>
    </mesh>
    {[-1.3, 1.3].map((z) => <group key={`light${z}`} position={[BODY_X, gantryHeight - 0.34, z]}>
      <mesh>
        <boxGeometry args={[0.9, 0.08, 0.2]}/>
        <meshStandardMaterial color="#e8fbff" emissive="#cdefff" emissiveIntensity={1.3} toneMapped={false}/>
      </mesh>
      <pointLight position={[0, -0.35, 0]} intensity={7} distance={4.2} decay={2} color="#dbf3ff"/>
    </group>)}

    <group position={[BODY_X - 1.5, gantryHeight, -1.85]}>
      <Beacon active={joining}/>
    </group>

    <group position={[padX - 0.05, 0, padZ - 1.15]} rotation={[0, 0.35, 0]}>
      <mesh position={[0, 0.66, 0]} castShadow>
        <boxGeometry args={[0.07, 1.32, 0.07]}/>
        <meshStandardMaterial color="#243c47" roughness={0.6} metalness={0.5}/>
      </mesh>
      <mesh position={[0, 1.42, 0]} rotation={[-0.3, 0, 0]} castShadow>
        <boxGeometry args={[0.66, 0.44, 0.05]}/>
        <meshStandardMaterial color="#0c1a21" roughness={0.5}/>
      </mesh>
      <mesh position={[0, 1.42, 0.028]} rotation={[-0.3, 0, 0]}>
        <planeGeometry args={[0.6, 0.38]}/>
        <meshStandardMaterial map={panel} emissiveMap={panel} emissive="#ffffff" emissiveIntensity={0.5} toneMapped={false}/>
      </mesh>
    </group>

    <Bollard position={[BODY_X - 1.62, 0, -2.02]} height={0.62}/>
    <Bollard position={[BODY_X - 1.62, 0, 2.02]} height={0.62}/>
  </group>;
}
