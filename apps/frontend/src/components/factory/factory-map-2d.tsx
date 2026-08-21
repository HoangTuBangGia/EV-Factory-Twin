"use client";

import { worldToScreen } from "@/lib/coordinate";
import { LANE_WIDTH } from "@/lib/factory-layout";
import type { FactoryLayout } from "@/schemas/factory";
import type { Robot } from "@/schemas/robot";
import type { FactoryMapLayers } from "./factory-map";

const STATION_COLOR = {
  BATTERY_BUFFER: "#2f7d8f",
  MARRIAGE_STATION: "#3f6ea8",
  CHARGING_STATION: "#2f8f7a",
} as const;

/**
 * Top-down fallback used when WebGL is unavailable. It reads from the same
 * layout object as the 3D scene, so a browser without WebGL still sees the true
 * station positions and routes rather than a stale sketch.
 */
export function FactoryMap2D({ robots, selectedRobotId, onSelect, layers, layout }: {
  robots: Robot[];
  selectedRobotId: string | null;
  onSelect: (id: string | null) => void;
  layers: FactoryMapLayers;
  layout: FactoryLayout;
}) {
  const { width: w, height: h } = layout;
  return <svg className="factory-map-2d" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="2D factory map">
    <defs>
      <pattern id="fm-grid" width="1" height="1" patternUnits="userSpaceOnUse">
        <path d="M 1 0 L 0 0 0 1" fill="none" stroke="#173039" strokeWidth=".035"/>
      </pattern>
      <pattern id="fm-hazard" width="1" height="1" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="1" height="1" fill="#1a1206"/>
        <rect width=".5" height="1" fill="#f4c236" opacity=".75"/>
      </pattern>
      <radialGradient id="fm-floor" cx="50%" cy="45%" r="72%">
        <stop offset="0%" stopColor="#142d38"/>
        <stop offset="100%" stopColor="#07131a"/>
      </radialGradient>
    </defs>

    <rect width={w} height={h} fill="url(#fm-floor)"/>
    <rect width={w} height={h} fill="url(#fm-grid)"/>

    {layers.routes && layout.routes.map((route) => {
      const path = route.waypoints
        .map((point, index) => `${index ? "L" : "M"}${point.x} ${h - point.y}`)
        .join(" ");
      return <g key={route.id}>
        <path className="fm-lane" d={path} strokeWidth={LANE_WIDTH}/>
        <path className="fm-lane-edge" d={path}/>
      </g>;
    })}

    {layers.stations && layout.stations.map((station) => {
      const color = STATION_COLOR[station.type];
      return <g key={station.id} className="fm-zone">
        <circle cx={station.x} cy={h - station.y} r=".7" fill={color} fillOpacity=".14" stroke={color} strokeWidth=".08"/>
        <text x={station.x + 0.22} y={h - station.y - 0.45} fill={color}>{station.type.replaceAll("_", " ")}</text>
      </g>;
    })}

    {layers.noGoZones && layout.no_go_zones.map((zone) => {
      const points = zone.points.map((point) => `${point.x},${h - point.y}`).join(" ");
      return <g key={zone.id} className="fm-zone fm-nogo">
        <polygon points={points} fill="url(#fm-hazard)" fillOpacity=".3" stroke="#fb7185" strokeWidth=".11"/>
        <text x={zone.points[0].x + 0.22} y={h - zone.points[0].y - 0.22} fill="#fb7185">NO-GO ZONE</text>
      </g>;
    })}

    {robots.map((robot) => {
      const point = worldToScreen(robot.pose.x, robot.pose.y, w, h, w, h);
      const low = robot.battery < 20;
      return <g
        key={robot.id}
        className={`robot-marker${low ? " low" : ""}${selectedRobotId === robot.id ? " selected" : ""}`}
        transform={`translate(${point.x} ${point.y}) rotate(${-robot.pose.yaw * 180 / Math.PI})`}
        onClick={() => onSelect(robot.id)}
        role="button" aria-label={`${robot.id}, ${robot.status}, battery ${Math.round(robot.battery)} percent`}
      >
        <circle r=".62"/>
        <path className="fm-heading" d="M.74 0 L.4 -.22 L.4 .22 Z"/>
        <g transform={`rotate(${robot.pose.yaw * 180 / Math.PI})`}>
          <text y="-.04">{robot.id}</text>
          <text y=".36" className="fm-battery">{Math.round(robot.battery)}%</text>
        </g>
      </g>;
    })}
  </svg>;
}
