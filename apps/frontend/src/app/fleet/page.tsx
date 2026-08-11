import { FleetTable } from "@/components/fleet/fleet-table";
import { RobotDrawer } from "@/components/fleet/robot-drawer";
export default function FleetPage(){return <><header className="page-head"><div><h2>Fleet</h2><p>Inspect robot state, battery, speed and assignments.</p></div></header><section className="panel"><div className="panel-head"><h3>AMR fleet</h3><span>Select a row for details</span></div><FleetTable/></section><RobotDrawer/></>}
