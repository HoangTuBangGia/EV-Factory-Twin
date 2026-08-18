"use client";

import { FACTORY_SIZE, worldToScreen } from "@/lib/coordinate";
import { LANE_WIDTH, MAIN_ROUTE, STATION_ANCHOR, ZONE, type WorldRect } from "@/lib/factory-layout";
import type { Robot } from "@/schemas/robot";

const W = FACTORY_SIZE.width, H = FACTORY_SIZE.height;

/** World rect to SVG rect, accounting for the flipped vertical axis. */
function svgRect(rect: WorldRect) {
  return { x: rect.x0, y: H - rect.y1, width: rect.x1 - rect.x0, height: rect.y1 - rect.y0 };
}

const ROUTE_PATH = MAIN_ROUTE
  .map((point, index) => `${index ? "L" : "M"}${point.x} ${H - point.y}`)
  .join(" ");

/**
 * Top-down fallback used when WebGL is unavailable. It reads from the same
 * layout constants as the 3D scene, so a browser without WebGL still sees the
 * true station positions and route rather than a stale sketch.
 */
export function FactoryMap2D({ robots, selectedRobotId, onSelect }: {
  robots: Robot[]; selectedRobotId: string | null; onSelect: (id: string | null) => void;
}) {
  return <svg className="factory-map-2d" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="2D factory map">
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

    <rect width={W} height={H} fill="url(#fm-floor)"/>
    <rect width={W} height={H} fill="url(#fm-grid)"/>

    <path className="fm-lane" d={ROUTE_PATH} strokeWidth={LANE_WIDTH}/>
    <path className="fm-lane-edge" d={ROUTE_PATH}/>

    {([
      ["BATTERY BUFFER", ZONE.BATTERY_BUFFER, "#2f7d8f"],
      ["MARRIAGE STATION", ZONE.MARRIAGE_STATION, "#3f6ea8"],
      ["CHARGING", ZONE.CHARGING_STATION, "#2f8f7a"],
      ["IDLE / STAGING", ZONE.IDLE_ZONE, "#6b8794"],
    ] as const).map(([name, rect, color]) => {
      const box = svgRect(rect);
      return <g key={name} className="fm-zone">
        <rect {...box} fill={color} fillOpacity=".14" stroke={color} strokeOpacity=".7" strokeWidth=".08"/>
        <text x={box.x + 0.22} y={box.y + 0.62} fill={color}>{name}</text>
      </g>;
    })}

    {(() => {
      const box = svgRect(ZONE.NO_GO);
      return <g className="fm-zone fm-nogo">
        <rect {...box} fill="url(#fm-hazard)" fillOpacity=".3"/>
        <rect {...box} fill="none" stroke="#fb7185" strokeWidth=".11"/>
        <text x={box.x + 0.22} y={box.y + 0.62} fill="#fb7185">NO-GO ZONE</text>
      </g>;
    })()}

    {Object.entries(STATION_ANCHOR).map(([id, anchor]) =>
      <circle key={id} className="fm-anchor" cx={anchor.x} cy={H - anchor.y} r=".13"/>)}

    {robots.map((robot) => {
      const point = worldToScreen(robot.pose.x, robot.pose.y, W, H, W, H);
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
