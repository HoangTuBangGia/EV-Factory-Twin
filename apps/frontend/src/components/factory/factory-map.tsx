"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BUFFER_SLOT_COUNT, defaultFactoryLayout } from "@/lib/factory-layout";
import type { FactoryLayout } from "@/schemas/factory";
import { useFactoryStore } from "@/stores/factory-store";
import { FactoryMap2D } from "./factory-map-2d";
import { FactoryPlantMap2D } from "./factory-plant-map-2d";
import { EV_FACTORY_DEPTH, EV_FACTORY_WIDTH } from "./scene/ev-factory-constants";

const FactoryScene = dynamic(
  () => import("./scene/factory-scene").then((module) => module.FactoryScene),
  { ssr: false, loading: () => <div className="map-loading"><span/>Building factory twin…</div> },
);

const LEGEND = [
  { label: "Reference plant", color: "#64748b" },
  { label: "Battery buffer", color: "#2f7d8f" },
  { label: "Marriage station", color: "#3f6ea8" },
  { label: "Charging", color: "#2f8f7a" },
  { label: "No-go", color: "#fb7185" },
  { label: "Congestion", color: "#f59e0b" },
  { label: "AMR route", color: "#7fe9dc" },
] as const;

type Support = "probing" | "webgl" | "fallback";

export interface FactoryMapProps {
  view?: "auto" | "2d";
  twoDimensionalVariant?: "layout" | "plant";
  layers?: FactoryMapLayers;
  layout?: FactoryLayout;
}

export interface FactoryMapLayers {
  stations: boolean;
  routes: boolean;
  noGoZones: boolean;
  congestionZones: boolean;
}

export const DEFAULT_FACTORY_MAP_LAYERS: FactoryMapLayers = {
  stations: true,
  routes: true,
  noGoZones: true,
  congestionZones: true,
};

const LAYER_BUTTONS = [
  ["stations", "Stations"],
  ["routes", "Routes"],
  ["noGoZones", "No-go zones"],
  ["congestionZones", "Congestion zones"],
] as const;

export function FactoryMapLayerControls({ layers, onChange }: {
  layers: FactoryMapLayers;
  onChange: (layers: FactoryMapLayers) => void;
}) {
  const allLayersVisible = Object.values(layers).every(Boolean);
  return <div className="factory-layer-controls" role="group" aria-label="Factory map layers">
    <button
      type="button" className={`filter ${allLayersVisible ? "active" : ""}`}
      aria-pressed={allLayersVisible}
      onClick={() => onChange({ ...DEFAULT_FACTORY_MAP_LAYERS })}
    >All layers</button>
    {LAYER_BUTTONS.map(([layer, label]) => <button
      key={layer}
      type="button" className={`filter ${layers[layer] ? "active" : ""}`}
      aria-pressed={layers[layer]}
      onClick={() => onChange({ ...layers, [layer]: !layers[layer] })}
    >{label}</button>)}
  </div>;
}

function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export function FactoryMap({
  view = "auto",
  twoDimensionalVariant = "layout",
  layers = DEFAULT_FACTORY_MAP_LAYERS,
  layout = defaultFactoryLayout,
}: FactoryMapProps) {
  const robotRecord = useFactoryStore((state) => state.robots);
  const robots = useMemo(() => Object.values(robotRecord), [robotRecord]);
  const selectedRobotId = useFactoryStore((state) => state.selectedRobotId);
  const selectRobot = useFactoryStore((state) => state.selectRobot);
  const queuedTasks = useFactoryStore((state) => state.metrics?.queued_tasks);

  const [support, setSupport] = useState<Support>(view === "2d" ? "fallback" : "probing");
  const [resetSignal, setResetSignal] = useState(0);

  useEffect(() => {
    setSupport(view === "2d" ? "fallback" : detectWebGL() ? "webgl" : "fallback");
  }, [view]);

  const resetView = useCallback(() => setResetSignal((value) => value + 1), []);

  // Charged packs waiting on the rack. Before the first metrics frame arrives the
  // buffer is shown at nominal capacity rather than empty.
  const bufferStock = queuedTasks === undefined
    ? BUFFER_SLOT_COUNT
    : Math.max(0, Math.min(BUFFER_SLOT_COUNT, queuedTasks));

  return <div className="factory-map" data-view={support === "webgl" ? "3d" : "2d"}>
    {support === "probing" && <div className="map-loading"><span/>Building factory twin…</div>}
    {support === "webgl" && <FactoryScene
      robots={robots} selectedRobotId={selectedRobotId} onSelect={selectRobot}
      bufferStock={bufferStock} resetSignal={resetSignal} layers={layers} layout={layout}
    />}
    {support === "fallback" && (twoDimensionalVariant === "plant"
      ? <FactoryPlantMap2D
          robots={robots} selectedRobotId={selectedRobotId} onSelect={selectRobot}
          layers={layers} layout={layout}
        />
      : <FactoryMap2D
          robots={robots} selectedRobotId={selectedRobotId} onSelect={selectRobot}
          layers={layers} layout={layout}
        />)}

    {twoDimensionalVariant !== "plant" && <div className="map-hud">
      <ul className="map-legend">
        {LEGEND.filter((item) => {
          if (item.label === "AMR route") return layers.routes;
          if (item.label === "No-go") return layers.noGoZones;
          if (item.label === "Congestion") return layers.congestionZones;
          if (item.label === "Reference plant") return true;
          return layers.stations;
        }).map((item) => <li key={item.label}>
          <i style={{ background: item.color }}/>{item.label}
        </li>)}
      </ul>
      <div className="map-scale">
        {support === "webgl"
          ? `Reference plant ${EV_FACTORY_WIDTH} × ${EV_FACTORY_DEPTH} m · applied layout ${layout.width} × ${layout.height} m`
          : `Applied layout ${layout.width} × ${layout.height} m · reference background`}
      </div>
      {support === "webgl" && <div className="map-hint">Drag to orbit · scroll to zoom</div>}
    </div>}
    {support === "webgl" && <button type="button" className="map-reset" onClick={resetView}>
      Reset view
    </button>}
  </div>;
}
