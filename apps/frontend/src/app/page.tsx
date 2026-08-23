"use client";

import { OverviewToolDock } from "@/components/dashboard/overview-tool-dock";
import { FactoryMap } from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";

export default function Overview() {
  return <section className="operations-cockpit" aria-label="EV Factory operations overview">
    <FactoryMap/>
    <OverviewToolDock/>
    <RobotDrawer/>
  </section>;
}
