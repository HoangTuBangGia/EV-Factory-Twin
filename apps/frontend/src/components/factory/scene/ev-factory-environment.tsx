"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import type { FactoryMapLayers } from "../factory-map";
import { EV_FACTORY_WIDTH } from "./ev-factory-constants";
import { buildFactoryScene } from "./ev-factory-map";

/**
 * Mounts the procedural EV-3D-map factory as the static environment around the
 * application's canonical, telemetry-driven AMRs. The prototype's demo AMRs
 * stay disabled so the screen never shows fabricated robots beside live ones.
 */
export function EvFactoryEnvironment({ layers }: { layers: FactoryMapLayers }) {
  const factory = useMemo(
    () => buildFactoryScene({ includeDemoAmrs: false }),
    [],
  );

  useFrame((_, delta) => factory.animate(delta));

  useEffect(() => {
    factory.setAmrRoutesVisible(false);
    factory.setLabelsVisible(layers.stations);
    factory.setSafetyZonesVisible(layers.noGoZones);
    factory.setGridVisible(true);
  }, [factory, layers.noGoZones, layers.stations]);

  useEffect(() => () => factory.dispose(), [factory]);

  return <group position={[-EV_FACTORY_WIDTH / 2, 0, 0]}>
    <primitive object={factory.scene}/>
  </group>;
}
