"use client";

import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import type { FactoryLayout, WorldPoint } from "@/schemas/factory";
import type { Robot } from "@/schemas/robot";
import type { FactoryMapLayers } from "./factory-map";
import {
  FACTORY_EQUIPMENT_DATA,
  FACTORY_ZONES,
  type MachineEquipment,
} from "./scene/ev-factory-data";

interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface HoveredItem {
  name: string;
  category: string;
  details: string;
  screenX: number;
  screenY: number;
}

type ViewPreset = "full" | "zone-a" | "zone-b" | "zone-c" | "u-line" | "robot";

export interface FactoryPlantMapEditor {
  routeDrawing: boolean;
  routeDraft: WorldPoint[];
  onStationMove: (stationId: string, point: WorldPoint) => void;
  onRoutePoint: (point: WorldPoint) => void;
  onRouteStation: (stationId: string) => void;
}

const FULL_VIEW: ViewBox = { x: -10, y: -26, width: 140, height: 52 };

function livePoint(point: WorldPoint, layout: FactoryLayout) {
  return { x: point.x, z: layout.height / 2 - point.y };
}

function cleanMeter(value: number) {
  return Math.round(value * 100) / 100;
}

function equipmentColors(type: MachineEquipment["type"]) {
  switch (type) {
    case "rack": return { fill: "#1d4ed8", stroke: "#60a5fa" };
    case "die_cast": return { fill: "#c2410c", stroke: "#fb923c" };
    case "robot_welder": return { fill: "#991b1b", stroke: "#f87171" };
    case "assembly_station": return { fill: "#047857", stroke: "#6ee7b7" };
    case "qc_station": return { fill: "#b91c1c", stroke: "#fca5a5" };
    case "loading_dock": return { fill: "#4338ca", stroke: "#a5b4fc" };
    case "inspection_station": return { fill: "#a16207", stroke: "#fde047" };
    case "ev_storage": return { fill: "#0e7490", stroke: "#67e8f9" };
    default: return { fill: "#334155", stroke: "#94a3b8" };
  }
}

function equipmentLabel(equipment: MachineEquipment) {
  switch (equipment.type) {
    case "rack": return equipment.id.replace("rack-a-row", "RACK K").toUpperCase();
    case "die_cast": return "GIGA-PRESS";
    case "robot_welder": return equipment.id.toUpperCase().replaceAll("-", " ");
    case "assembly_station": return equipment.id.toUpperCase().replace("ASSEMBLY-", "STATION ");
    case "qc_station": return equipment.id.toUpperCase().replaceAll("-", " ");
    case "loading_dock": return equipment.id.toUpperCase().replaceAll("-", " ");
    case "inspection_station": return "INSPECTION";
    default: return equipment.name;
  }
}

export function FactoryPlantMap2D({
  robots, selectedRobotId, onSelect, layers, layout, editor,
}: {
  robots: Robot[];
  selectedRobotId: string | null;
  onSelect: (id: string | null) => void;
  layers: FactoryMapLayers;
  layout: FactoryLayout;
  editor?: FactoryPlantMapEditor;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [viewBox, setViewBox] = useState<ViewBox>(FULL_VIEW);
  const [activePreset, setActivePreset] = useState<ViewPreset>("full");
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [showGrid, setShowGrid] = useState(true);
  const [showDimensions, setShowDimensions] = useState(true);
  const [showFlow, setShowFlow] = useState(true);
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [measureStart, setMeasureStart] = useState<{ x: number; z: number } | null>(null);
  const [measureCurrent, setMeasureCurrent] = useState<{ x: number; z: number } | null>(null);
  const [measureEnd, setMeasureEnd] = useState<{ x: number; z: number } | null>(null);
  const [hoveredItem, setHoveredItem] = useState<HoveredItem | null>(null);
  const [draggingStationId, setDraggingStationId] = useState<string | null>(null);

  const trackedRobot = robots[0] ?? null;
  const trackedPoint = useMemo(
    () => trackedRobot ? livePoint(trackedRobot.pose, layout) : null,
    [layout, trackedRobot],
  );

  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, z: 0 };
    const matrix = svg.getScreenCTM();
    if (!matrix) return { x: 0, z: 0 };
    const point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    const world = point.matrixTransform(matrix.inverse());
    return { x: world.x, z: world.y };
  }, []);

  const screenToLayout = useCallback((clientX: number, clientY: number) => {
    const point = screenToWorld(clientX, clientY);
    const snap = (value: number) => Math.round(value * 2) / 2;
    return {
      x: Math.min(layout.width, Math.max(0, snap(point.x))),
      y: Math.min(layout.height, Math.max(0, snap(layout.height / 2 - point.z))),
    };
  }, [layout.height, layout.width, screenToWorld]);

  function setPreset(preset: ViewPreset) {
    setActivePreset(preset);
    if (preset === "full") setViewBox(FULL_VIEW);
    if (preset === "zone-a") setViewBox({ x: -4, y: -19, width: 48, height: 38 });
    if (preset === "zone-b") setViewBox({ x: 36, y: -24, width: 58, height: 48 });
    if (preset === "zone-c") setViewBox({ x: 86, y: -19, width: 40, height: 38 });
    if (preset === "u-line") setViewBox({ x: 43, y: -1, width: 46, height: 23 });
    if (preset === "robot" && trackedPoint) {
      setViewBox({ x: trackedPoint.x - 12, y: trackedPoint.z - 8, width: 24, height: 16 });
    }
  }

  function zoom(direction: "in" | "out") {
    const factor = direction === "in" ? 0.8 : 1.25;
    setViewBox((current) => ({
      x: current.x + current.width * (1 - factor) / 2,
      y: current.y + current.height * (1 - factor) / 2,
      width: Math.min(Math.max(current.width * factor, 15), 250),
      height: Math.min(Math.max(current.height * factor, 8), 120),
    }));
  }

  function handlePointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    if (editor?.routeDrawing) {
      editor.onRoutePoint(screenToLayout(event.clientX, event.clientY));
      return;
    }
    if (isMeasuring) {
      const point = screenToWorld(event.clientX, event.clientY);
      if (!measureStart || measureEnd) {
        setMeasureStart(point);
        setMeasureCurrent(point);
        setMeasureEnd(null);
      } else {
        setMeasureEnd(point);
        setMeasureCurrent(null);
      }
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsPanning(true);
    setPanStart({ x: event.clientX, y: event.clientY });
  }

  function handlePointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    if (draggingStationId && editor) {
      editor.onStationMove(
        draggingStationId,
        screenToLayout(event.clientX, event.clientY),
      );
      return;
    }
    if (isMeasuring && measureStart && !measureEnd) {
      setMeasureCurrent(screenToWorld(event.clientX, event.clientY));
      return;
    }
    if (!isPanning) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const dx = (event.clientX - panStart.x) * viewBox.width / rect.width;
    const dy = (event.clientY - panStart.y) * viewBox.height / rect.height;
    setViewBox((current) => ({ ...current, x: current.x - dx, y: current.y - dy }));
    setPanStart({ x: event.clientX, y: event.clientY });
  }

  function handlePointerUp(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setIsPanning(false);
    setDraggingStationId(null);
  }

  function handleWheel(event: ReactWheelEvent<SVGSVGElement>) {
    event.preventDefault();
    const factor = event.deltaY > 0 ? 1.15 : 0.87;
    const mouse = screenToWorld(event.clientX, event.clientY);
    setViewBox((current) => {
      const width = Math.min(Math.max(current.width * factor, 15), 250);
      const height = Math.min(Math.max(current.height * factor, 8), 120);
      return {
        x: mouse.x - (mouse.x - current.x) * width / current.width,
        y: mouse.z - (mouse.z - current.y) * height / current.height,
        width,
        height,
      };
    });
  }

  function toggleMeasurement() {
    setIsMeasuring((current) => !current);
    setMeasureStart(null);
    setMeasureCurrent(null);
    setMeasureEnd(null);
  }

  function exportSvg() {
    const svg = svgRef.current;
    if (!svg) return;
    const blob = new Blob([new XMLSerializer().serializeToString(svg)], {
      type: "image/svg+xml;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "EV_Factory_TopDown_2D_Map.svg";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const measurementTarget = measureEnd ?? measureCurrent;
  const measurement = measureStart && measurementTarget
    ? Math.hypot(measurementTarget.x - measureStart.x, measurementTarget.z - measureStart.z)
    : null;

  return <div className="plant-map-2d">
    <div className="plant-map-presets" aria-label="2D factory view presets">
      <strong>2D CAD</strong>
      {([
        ["full", "Full map"],
        ["zone-a", "Zone A"],
        ["zone-b", "Zone B"],
        ["zone-c", "Zone C"],
        ["u-line", "U-line"],
      ] as const).map(([preset, label]) => <button
        key={preset} type="button" className={activePreset === preset ? "active" : ""}
        onClick={() => setPreset(preset)}
      >{label}</button>)}
      {trackedRobot && <button
        type="button" className={activePreset === "robot" ? "active" : ""}
        onClick={() => setPreset("robot")}
      >Track {trackedRobot.id}</button>}
    </div>

    <div className="plant-map-tools" aria-label="2D factory map tools">
      <button type="button" className={showGrid ? "active" : ""} onClick={() => setShowGrid((value) => !value)}>Grid</button>
      <button type="button" className={showDimensions ? "active" : ""} onClick={() => setShowDimensions((value) => !value)}>Dimensions</button>
      <button type="button" className={showFlow ? "active" : ""} onClick={() => setShowFlow((value) => !value)}>Flow</button>
      <button type="button" className={isMeasuring ? "active measuring" : ""} onClick={toggleMeasurement}>Measure</button>
      <button type="button" onClick={exportSvg}>Export SVG</button>
    </div>

    <div className="plant-map-zoom" aria-label="2D map zoom controls">
      <button type="button" aria-label="Zoom in" onClick={() => zoom("in")}>+</button>
      <button type="button" aria-label="Zoom out" onClick={() => zoom("out")}>−</button>
      <button type="button" aria-label="Reset 2D view" onClick={() => setPreset("full")}>↺</button>
    </div>

    {isMeasuring && <div className="plant-measurement" role="status">
      <strong>Metric measurement</strong>
      <span>{measurement === null ? "Select the first point" : `${measurement.toFixed(2)} m`}</span>
    </div>}

    <svg
      ref={svgRef}
      className={`factory-map-2d plant-map-canvas${isMeasuring ? " measuring" : isPanning ? " panning" : ""}`}
      viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="2D EV factory plant map"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onWheel={handleWheel}
    >
      <defs>
        <pattern id="plant-grid-1m" width="1" height="1" patternUnits="userSpaceOnUse">
          <path d="M1 0H0V1" fill="none" stroke="#1e293b" strokeWidth=".04"/>
        </pattern>
        <pattern id="plant-grid-5m" width="5" height="5" patternUnits="userSpaceOnUse">
          <rect width="5" height="5" fill="url(#plant-grid-1m)"/>
          <path d="M5 0H0V5" fill="none" stroke="#334155" strokeWidth=".08"/>
        </pattern>
        <pattern id="plant-hazard" width="2" height="2" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <rect width="2" height="2" fill="#1e293b"/>
          <rect width=".8" height="2" fill="#ef4444" opacity=".65"/>
        </pattern>
        <marker id="plant-flow-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto">
          <path d="M0 1.5L8 5 0 8.5Z" fill="#34d399"/>
        </marker>
        <marker id="plant-dim-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto-start-reverse">
          <path d="M0 2L6 5 0 8Z" fill="#94a3b8"/>
        </marker>
      </defs>

      <rect x="-30" y="-40" width="180" height="80" fill="#090d16"/>
      {showGrid && <rect x="-10" y="-26" width="140" height="52" fill="url(#plant-grid-5m)"/>}

      <g className="plant-zones">
        {FACTORY_ZONES.map((zone) => <g
          key={zone.id} className="plant-zone"
          onMouseEnter={(event) => setHoveredItem({
            name: zone.nameEn,
            category: zone.code,
            details: `${zone.dimensions.length} × ${zone.dimensions.width} m`,
            screenX: event.clientX,
            screenY: event.clientY,
          })}
          onMouseLeave={() => setHoveredItem(null)}
        >
          <rect
            x={zone.dimensions.xStart} y={zone.dimensions.zStart}
            width={zone.dimensions.length} height={zone.dimensions.width}
            fill={zone.id === "zone-b" ? "#0f172a" : "#1e293b"}
            stroke={zone.id === "zone-a" ? "#3b82f6" : zone.id === "zone-b" ? "#eab308" : "#ef4444"}
            strokeWidth=".3" rx=".5"
          />
          {zone.subZones?.map((subZone) => <rect
            key={subZone.id}
            x={subZone.bounds.x - subZone.bounds.w / 2}
            y={subZone.bounds.z - subZone.bounds.d / 2}
            width={subZone.bounds.w} height={subZone.bounds.d}
            fill={subZone.color} fillOpacity=".12" stroke={subZone.color}
            strokeWidth=".13" strokeDasharray=".6 .3"
          />)}
          <text
            x={(zone.dimensions.xStart + zone.dimensions.xEnd) / 2}
            y={(zone.dimensions.zStart + zone.dimensions.zEnd) / 2}
            className="plant-zone-watermark"
          >{zone.code}</text>
          <text
            x={(zone.dimensions.xStart + zone.dimensions.xEnd) / 2}
            y={zone.dimensions.zStart - 1}
            className="plant-zone-label"
          >{zone.nameEn}</text>
        </g>)}
      </g>

      <g className="plant-walls" fill="none" stroke="#94a3b8">
        <polyline points="0,-15 0,15 40,15 40,20 90,20 90,15 120,15 120,-15 90,-15 90,-20 40,-20 40,-15 0,-15" strokeWidth=".55"/>
        <path d="M40 -15V-2.5M40 2.5V15M90 -15V-2.5M90 2.5V15" strokeWidth=".65"/>
        <rect x="39.6" y="-2.5" width=".8" height="5" fill="#eab308" fillOpacity=".35" stroke="#eab308" strokeWidth=".1"/>
        <rect x="89.6" y="-2.5" width=".8" height="5" fill="#eab308" fillOpacity=".35" stroke="#eab308" strokeWidth=".1"/>
      </g>

      {layers.noGoZones && <g className="plant-no-go">
        {layout.no_go_zones.map((zone) => <polygon
          key={zone.id}
          points={zone.points.map((point) => {
            const mapped = livePoint(point, layout);
            return `${mapped.x},${mapped.z}`;
          }).join(" ")}
          fill="url(#plant-hazard)" fillOpacity=".45" stroke="#fb7185" strokeWidth=".15"
        />)}
      </g>}

      {layers.routes && <g className="plant-routes">
        {layout.routes.map((route) => <path
          key={route.id} className="fm-lane plant-live-route"
          d={route.waypoints.map((point, index) => {
            const mapped = livePoint(point, layout);
            return `${index ? "L" : "M"}${mapped.x} ${mapped.z}`;
          }).join(" ")}
          fill="none" stroke="#7fe9dc" strokeWidth=".42" strokeDasharray=".8 .35"
          markerEnd={showFlow ? "url(#plant-flow-arrow)" : undefined}
        />)}
        {editor?.routeDrawing && editor.routeDraft.length > 0 && <path
          className="plant-route-draft"
          d={editor.routeDraft.map((point, index) => {
            const mapped = livePoint(point, layout);
            return `${index ? "L" : "M"}${mapped.x} ${mapped.z}`;
          }).join(" ")}
          fill="none" stroke="#facc15" strokeWidth=".55" strokeDasharray=".65 .3"
        />}
      </g>}

      {layers.stations && <g className="plant-equipment-layer">
        {FACTORY_EQUIPMENT_DATA.map((equipment) => {
          const [centerX, , centerZ] = equipment.position;
          const [width, , depth] = equipment.dimensions;
          const x = centerX - width / 2;
          const z = centerZ - depth / 2;
          const colors = equipmentColors(equipment.type);
          return <g
            key={equipment.id} className={`plant-equipment ${equipment.type}`}
            onMouseEnter={(event) => setHoveredItem({
              name: equipment.name,
              category: equipment.type.replaceAll("_", " ").toUpperCase(),
              details: `${width} × ${depth} m · ${equipment.status}`,
              screenX: event.clientX,
              screenY: event.clientY,
            })}
            onMouseLeave={() => setHoveredItem(null)}
          >
            <rect x={x} y={z} width={width} height={depth} rx=".25" fill={colors.fill} stroke={colors.stroke} strokeWidth=".2"/>
            {equipment.type === "rack" && <path
              d={`M${x + width * .25} ${z}V${z + depth}M${x + width * .5} ${z}V${z + depth}M${x + width * .75} ${z}V${z + depth}`}
              stroke="#bfdbfe" strokeWidth=".08"
            />}
            {equipment.type === "robot_welder" && <circle
              cx={centerX} cy={centerZ} r={Math.min(width, depth) * .3}
              fill="none" stroke="#fecaca" strokeWidth=".12" strokeDasharray=".3 .2"
            />}
            {equipment.type === "die_cast" && <circle cx={centerX - width * .2} cy={centerZ} r="1.4" fill="#7c2d12" stroke="#fed7aa" strokeWidth=".12"/>}
            <text x={centerX} y={centerZ + .22} className="plant-equipment-label">{equipmentLabel(equipment)}</text>
          </g>;
        })}

        {layout.stations.map((station) => {
          const point = livePoint(station, layout);
          return <g
            key={station.id}
            className={`fm-zone plant-live-station${editor ? " editable" : ""}`}
            role={editor ? "button" : undefined}
            tabIndex={editor ? 0 : undefined}
            aria-label={editor ? `Route station ${station.id}` : undefined}
            onPointerDown={(event) => {
              if (!editor) return;
              event.stopPropagation();
              if (editor.routeDrawing) {
                editor.onRouteStation(station.id);
                return;
              }
              svgRef.current?.setPointerCapture(event.pointerId);
              setDraggingStationId(station.id);
            }}
            onKeyDown={(event) => {
              if (!editor?.routeDrawing || (event.key !== "Enter" && event.key !== " ")) return;
              editor.onRouteStation(station.id);
            }}
          >
            <circle cx={point.x} cy={point.z} r=".75"/>
            <text x={point.x + 1} y={point.z - .65}>{station.type.replaceAll("_", " ")}</text>
          </g>;
        })}
      </g>}

      <g id="live-amr-fleet-2d">
        {robots.map((robot) => {
          const point = livePoint(robot.pose, layout);
          const x = cleanMeter(point.x);
          const z = cleanMeter(point.z);
          const angle = cleanMeter(-robot.pose.yaw * 180 / Math.PI);
          const low = robot.battery < 20;
          return <g
            key={robot.id}
            data-robot-id={robot.id}
            className={`robot-marker${low ? " low" : ""}${selectedRobotId === robot.id ? " selected" : ""}`}
            transform={`translate(${x} ${z}) rotate(${angle})`}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={() => onSelect(robot.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") onSelect(robot.id);
            }}
            onMouseEnter={(event) => setHoveredItem({
              name: robot.name,
              category: `${robot.id} · ${robot.status}`,
              details: `Battery ${Math.round(robot.battery)}% · ${robot.velocity.linear.toFixed(1)} m/s`,
              screenX: event.clientX,
              screenY: event.clientY,
            })}
            onMouseLeave={() => setHoveredItem(null)}
            role="button"
            tabIndex={0}
            aria-label={`${robot.id}, ${robot.status}, battery ${Math.round(robot.battery)} percent`}
          >
            <rect x="-.8" y="-.5" width="1.6" height="1" rx=".2"/>
            <rect className="plant-amr-payload" x="-.5" y="-.34" width="1" height=".68" rx=".1"/>
            <path className="fm-heading" d="M.76 0L.4-.24V.24Z"/>
            <circle className="plant-amr-beacon" r=".12"/>
            <g transform={`rotate(${-angle})`}>
              <text y="-.72">{robot.id}</text>
              <text y=".92" className="fm-battery">{Math.round(robot.battery)}%</text>
            </g>
          </g>;
        })}
      </g>

      {showDimensions && <g className="plant-dimensions" stroke="#94a3b8" strokeWidth=".1">
        <line x1="0" y1="-23" x2="120" y2="-23" stroke="#60a5fa" strokeWidth=".15" markerStart="url(#plant-dim-arrow)" markerEnd="url(#plant-dim-arrow)"/>
        <line x1="0" y1="-23.8" x2="0" y2="-15.5" strokeDasharray=".3 .3"/>
        <line x1="120" y1="-23.8" x2="120" y2="-15.5" strokeDasharray=".3 .3"/>
        <text x="60" y="-23.8">TOTAL LENGTH · 120.00 m</text>
        <line x1="-3" y1="-15" x2="-3" y2="15" markerStart="url(#plant-dim-arrow)" markerEnd="url(#plant-dim-arrow)"/>
        <text x="-4" y="0" transform="rotate(-90 -4 0)">ZONE A WIDTH · 30.0 m</text>
        <line x1="37" y1="-20" x2="37" y2="20" markerStart="url(#plant-dim-arrow)" markerEnd="url(#plant-dim-arrow)"/>
        <text x="36" y="0" transform="rotate(-90 36 0)">ZONE B WIDTH · 40.0 m</text>
      </g>}

      {isMeasuring && measureStart && measurementTarget && <g className="plant-measure-line">
        <line x1={measureStart.x} y1={measureStart.z} x2={measurementTarget.x} y2={measurementTarget.z}/>
        <circle cx={measureStart.x} cy={measureStart.z} r=".5"/>
        <circle cx={measurementTarget.x} cy={measurementTarget.z} r=".5"/>
        <text x={(measureStart.x + measurementTarget.x) / 2} y={(measureStart.z + measurementTarget.z) / 2 - .7}>
          {measurement?.toFixed(2)} m
        </text>
      </g>}
    </svg>

    {hoveredItem && <div
      className="plant-map-tooltip"
      style={{ left: hoveredItem.screenX + 12, top: hoveredItem.screenY + 12 }}
    >
      <small>{hoveredItem.category}</small>
      <strong>{hoveredItem.name}</strong>
      <span>{hoveredItem.details}</span>
    </div>}

    <div className="plant-map-scale">
      <strong>1 unit = 1 m</strong>
      <span>EV plant · 120 × 40 m</span>
      <span>Live layout · {layout.width} × {layout.height} m</span>
    </div>
    <div className="plant-map-legend" aria-hidden="true">
      <span><i className="zone-a"/>Warehouse</span>
      <span><i className="zone-b"/>Production</span>
      <span><i className="zone-c"/>Shipping / QC</span>
      <span><i className="live"/>Live telemetry</span>
    </div>
  </div>;
}
