"use client";

import { useState } from "react";
import { AlertList } from "@/components/alerts/alert-list";
import {
  DEFAULT_FACTORY_MAP_LAYERS,
  FactoryMap,
  type FactoryMapLayers,
} from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";

export default function FactoryPage() {
  const [layers, setLayers] = useState<FactoryMapLayers>(DEFAULT_FACTORY_MAP_LAYERS);
  const allLayersVisible = Object.values(layers).every(Boolean);

  function toggleLayer(layer: keyof FactoryMapLayers) {
    setLayers((current) => ({ ...current, [layer]: !current[layer] }));
  }

  return <>
    <header className="page-head">
      <div>
        <h2>Factory Digital Twin</h2>
        <p>Realtime 2D visualization using factory-meter coordinates.</p>
      </div>
      <div className="toolbar" aria-label="Factory map layers">
        <button
          type="button"
          className={`filter ${allLayersVisible ? "active" : ""}`}
          aria-pressed={allLayersVisible}
          onClick={() => setLayers(DEFAULT_FACTORY_MAP_LAYERS)}
        >All layers</button>
        <button
          type="button"
          className={`filter ${layers.stations ? "active" : ""}`}
          aria-pressed={layers.stations}
          onClick={() => toggleLayer("stations")}
        >Stations</button>
        <button
          type="button"
          className={`filter ${layers.routes ? "active" : ""}`}
          aria-pressed={layers.routes}
          onClick={() => toggleLayer("routes")}
        >Routes</button>
        <button
          type="button"
          className={`filter ${layers.noGoZones ? "active" : ""}`}
          aria-pressed={layers.noGoZones}
          onClick={() => toggleLayer("noGoZones")}
        >No-go zones</button>
      </div>
    </header>
    <div className="grid main-grid factory-page-grid">
      <section className="panel factory-map-panel">
        <div className="panel-head">
          <h3>EV production plant</h3>
          <span>Click an AMR to inspect</span>
        </div>
        <FactoryMap view="2d" twoDimensionalVariant="plant" layers={layers}/>
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
