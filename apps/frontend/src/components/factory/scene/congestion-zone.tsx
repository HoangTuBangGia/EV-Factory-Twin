"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { toScene } from "@/lib/factory-layout";
import type { CongestionZone as CongestionZoneData, FactoryLayout } from "@/schemas/factory";

/** Applied-layout delay area. This is operational geometry, not part of the reference plant. */
export function CongestionZone({ zone, layout }: {
  zone: CongestionZoneData;
  layout: FactoryLayout;
}) {
  const shape = useMemo(() => {
    const polygon = new THREE.Shape();
    zone.points.forEach((point, index) => {
      const [x, , z] = toScene(point, layout);
      if (index === 0) polygon.moveTo(x, -z);
      else polygon.lineTo(x, -z);
    });
    polygon.closePath();
    return polygon;
  }, [layout, zone.points]);

  return <mesh position={[0, 0.024, 0]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={4}>
    <shapeGeometry args={[shape]}/>
    <meshBasicMaterial
      color="#f59e0b" transparent opacity={0.24}
      side={THREE.DoubleSide} depthWrite={false}
    />
  </mesh>;
}
