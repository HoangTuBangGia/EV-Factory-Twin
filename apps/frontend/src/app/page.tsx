"use client";

import { OverviewToolDock } from "@/components/dashboard/overview-tool-dock";
import { FactoryMap } from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
import { useAppliedFactoryLayout } from "@/hooks/use-applied-factory-layout";

export default function Overview() {
  const layout = useAppliedFactoryLayout();
  return <section className="operations-cockpit" aria-label="EV Factory operations overview">
    <FactoryMap layout={layout}/>
    <OverviewToolDock/>
    <RobotDrawer/>
  </section>;
}
