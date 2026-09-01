"use client";

import { useState } from "react";
import LayoutsPage from "@/app/layouts/page";
import { AlertList } from "@/components/alerts/alert-list";
import { useAuth } from "@/components/auth/auth-provider";
import {
  DEFAULT_FACTORY_MAP_LAYERS,
  FactoryMap,
  FactoryMapLayerControls,
  type FactoryMapLayers,
} from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
import { useAppliedFactoryLayout } from "@/hooks/use-applied-factory-layout";
import { can } from "@/lib/auth/permissions";

export default function FactoryPage() {
  const { user } = useAuth();
  const [layers, setLayers] = useState<FactoryMapLayers>(DEFAULT_FACTORY_MAP_LAYERS);
  const layout = useAppliedFactoryLayout();
  const [editing, setEditing] = useState(false);

  if (editing) return <>
    <div className="factory-editor-return">
      <button className="button" type="button" onClick={() => setEditing(false)}>
        Return to live view
      </button>
    </div>
    <LayoutsPage/>
  </>;

  return <>
    <header className="page-head">
      <div>
        <h2>Factory Digital Twin</h2>
        <p>Realtime AMR overlays on reference 2D factory geometry.</p>
      </div>
      <div className="toolbar" aria-label="Factory map layers">
        {can(user?.role, "layout:edit") && <button
          type="button" className="filter" onClick={() => setEditing(true)}
        >Edit layout</button>}
        <FactoryMapLayerControls layers={layers} onChange={setLayers}/>
      </div>
    </header>
    <div className="grid main-grid factory-page-grid">
      <section className="panel factory-map-panel">
        <div className="panel-head">
          <h3>{layout.name}</h3>
          <span>{layout.id} · v{layout.version} · click an AMR to inspect</span>
        </div>
        <FactoryMap view="2d" twoDimensionalVariant="plant" layers={layers} layout={layout}/>
      </section>
      <section className="panel factory-alert-panel">
        <div className="panel-head">
          <h3>Active alerts</h3>
          <span>Live feed</span>
        </div>
        <div className="factory-alert-scroll">
          <AlertList/>
        </div>
      </section>
    </div>
    <RobotDrawer/>
  </>;
}
