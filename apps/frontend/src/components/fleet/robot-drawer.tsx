"use client";

import { useFactoryStore } from "@/stores/factory-store";
import { Battery } from "./battery";
import { StatusBadge } from "./status-badge";

export function RobotDrawer() {
  const id = useFactoryStore((s) => s.selectedRobotId); const robot = useFactoryStore((s) => id ? s.robots[id] : undefined); const close = useFactoryStore((s) => s.selectRobot);
  if (!robot) return null;
  return <aside className="drawer" aria-label="Robot details"><div className="drawer-head"><div><div className="eyebrow">Robot details</div><h2>{robot.id}</h2><span className="muted">{robot.name}</span></div><button className="close" onClick={() => close(null)} aria-label="Close">×</button></div><div style={{marginTop:20}}><StatusBadge value={robot.status}/></div><div className="detail-grid"><div className="detail"><small>Battery</small><Battery value={robot.battery}/></div><div className="detail"><small>Speed</small><strong>{robot.velocity.linear.toFixed(1)} m/s</strong></div><div className="detail"><small>Position X</small><strong>{robot.pose.x.toFixed(2)} m</strong></div><div className="detail"><small>Position Y</small><strong>{robot.pose.y.toFixed(2)} m</strong></div><div className="detail"><small>Yaw</small><strong>{robot.pose.yaw.toFixed(2)} rad</strong></div><div className="detail"><small>Current task</small><strong>{robot.task_id ?? "None"}</strong></div><div className="detail"><small>Payload</small><strong>{robot.payload_id ?? "None"}</strong></div><div className="detail"><small>Last seen</small><strong>{new Date(robot.last_seen_at).toLocaleTimeString()}</strong></div></div></aside>;
}
