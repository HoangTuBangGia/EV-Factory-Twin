"use client";

import { useEffect, useState } from "react";
import { AlertList } from "@/components/alerts/alert-list";
import {
  DEFAULT_FACTORY_MAP_LAYERS,
  FactoryMap,
  type FactoryMapLayers,
} from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
import { apiClient } from "@/lib/api-client";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { latestAppliedScenario, projectLayoutVersion } from "@/lib/layout-projection";
import type { FactoryLayout } from "@/schemas/factory";
import { useFactoryStore } from "@/stores/factory-store";

export default function FactoryPage() {
  const [layers, setLayers] = useState<FactoryMapLayers>(DEFAULT_FACTORY_MAP_LAYERS);
  const [layout, setLayout] = useState<FactoryLayout>(defaultFactoryLayout);
  const factoryRevision = useFactoryStore((state) => state.factoryRevision);
  const allLayersVisible = Object.values(layers).every(Boolean);

  useEffect(() => {
    let active = true;
    void apiClient.getScenarios()
      .then(async (scenarios) => {
        const applied = latestAppliedScenario(scenarios);
        if (!applied) return;
        const version = await apiClient.getLayoutVersion(
          applied.config.layout_id,
          applied.config.layout_version,
        );
        if (active) setLayout(projectLayoutVersion(version));
      })
      .catch(() => {
        // Runtime telemetry remains usable with the documented default layout.
      });
    return () => { active = false; };
  }, [factoryRevision]);

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
