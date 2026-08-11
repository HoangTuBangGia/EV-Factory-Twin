import { AlertList } from "@/components/alerts/alert-list";
import { FactoryMap } from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";

export default function FactoryPage(){return <><header className="page-head"><div><h2>Factory Digital Twin</h2><p>Realtime 2D visualization using factory-meter coordinates.</p></div><div className="toolbar"><button className="filter active">All layers</button><button className="filter">Routes</button><button className="filter">No-go zones</button></div></header><div className="grid main-grid"><section className="panel"><div className="panel-head"><h3>Battery transfer zone</h3><span>Click an AMR to inspect</span></div><FactoryMap/></section><section className="panel"><div className="panel-head"><h3>Active alerts</h3><span>Last known state retained</span></div><div className="panel-body"><AlertList/></div></section></div><RobotDrawer/></>}
