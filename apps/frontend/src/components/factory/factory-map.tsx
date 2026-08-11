"use client";

import { useMemo } from "react";
import { FACTORY_SIZE, worldToScreen } from "@/lib/coordinate";
import { useFactoryStore } from "@/stores/factory-store";

const W=20, H=15;
export function FactoryMap() {
  const robotRecord = useFactoryStore((s) => s.robots); const robots = useMemo(() => Object.values(robotRecord), [robotRecord]); const selected = useFactoryStore((s) => s.selectedRobotId); const select = useFactoryStore((s) => s.selectRobot);
  return <div className="factory-map"><svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="2D factory map">
    <defs><pattern id="grid" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M 1 0 L 0 0 0 1" fill="none" stroke="#173039" strokeWidth=".035"/></pattern></defs>
    <rect width={W} height={H} fill="url(#grid)"/><path className="route" d="M4 11 H16 V4 H4 V11 M9 11 V4"/>
    <rect className="zone" x="1" y="9" width="4" height="4"/><text className="zone-label" x="1.3" y="9.7">BATTERY BUFFER</text>
    <rect className="zone" x="15" y="1.5" width="4" height="4"/><text className="zone-label" x="15.3" y="2.2">MARRIAGE STATION</text>
    <rect className="zone" x="1" y="1" width="4" height="2.7"/><text className="zone-label" x="1.3" y="1.7">CHARGING</text>
    <rect x="8.3" y="6.2" width="2" height="2" fill="#3b1720" stroke="#fb7185" strokeWidth=".1" opacity=".7"/><text className="zone-label" x="8.55" y="7.3" fill="#fb7185">NO-GO</text>
    {robots.map((r) => { const p=worldToScreen(r.pose.x,r.pose.y,FACTORY_SIZE.width,FACTORY_SIZE.height,W,H); return <g key={r.id} className={`robot-marker ${r.battery<20?"low":""} ${selected===r.id?"selected":""}`} transform={`translate(${p.x} ${p.y}) rotate(${r.pose.yaw*180/Math.PI})`} onClick={() => select(r.id)} role="button" aria-label={`${r.id}, ${r.status}`}>
      <circle r=".65"/><path className="robot-arrow" d="M.75 0 L.42 -.2 L.42 .2 Z"/><text transform={`rotate(${-r.pose.yaw*180/Math.PI})`} y="-.05">{r.id}</text><text transform={`rotate(${-r.pose.yaw*180/Math.PI})`} y=".35">{Math.round(r.battery)}%</text>
    </g>; })}
  </svg></div>;
}
