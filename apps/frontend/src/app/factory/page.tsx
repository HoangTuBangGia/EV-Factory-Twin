import { AlertList } from "@/components/alerts/alert-list";
import { FactoryMap } from "@/components/factory/factory-map";
import { RobotDrawer } from "@/components/fleet/robot-drawer";

export default function FactoryPage() {
  return <>
    <header className="page-head">
      <div>
        <h2>Factory Digital Twin</h2>
        <p>Realtime 2D visualization using factory-meter coordinates.</p>
      </div>
      <div className="toolbar">
        <button className="filter active">All layers</button>
        <button className="filter">Routes</button>
        <button className="filter">No-go zones</button>
      </div>
    </header>
    <div className="grid main-grid factory-page-grid">
      <section className="panel factory-map-panel">
        <div className="panel-head">
          <h3>Battery transfer zone</h3>
          <span>Click an AMR to inspect</span>
        </div>
        <FactoryMap view="2d"/>
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
