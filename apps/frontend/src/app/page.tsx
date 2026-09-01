"use client";

import { useState } from "react";
import { OverviewToolDock } from "@/components/dashboard/overview-tool-dock";
import {
  DEFAULT_FACTORY_MAP_LAYERS,
  FactoryMap,
  FactoryMapLayerControls,
  type FactoryMapLayers,
} from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
import { useAppliedFactoryLayout } from "@/hooks/use-applied-factory-layout";

export default function Overview() {
  const layout = useAppliedFactoryLayout();
  const [layers, setLayers] = useState<FactoryMapLayers>(DEFAULT_FACTORY_MAP_LAYERS);
  return <section className="operations-cockpit" aria-label="EV Factory operations overview">
    <FactoryMap layout={layout} layers={layers}/>
    <div className="overview-map-layers">
      <FactoryMapLayerControls layers={layers} onChange={setLayers}/>
    </div>
    <OverviewToolDock/>
    <RobotDrawer/>
  </section>;
}
