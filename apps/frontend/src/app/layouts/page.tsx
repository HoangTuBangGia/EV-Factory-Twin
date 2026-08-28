"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { FactoryPlantMap2D } from "@/components/factory/factory-plant-map-2d";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { projectLayoutVersion } from "@/lib/layout-projection";
import { candidateForLayoutVersion } from "@/lib/workflow";
import type { FactoryLayout, WorldPoint } from "@/schemas/factory";
import {
  layoutVersionContentSchema,
  type LayoutSummary,
  type LayoutVersion,
  type LayoutVersionContent,
} from "@/schemas/layout";
import { useFactoryStore } from "@/stores/factory-store";

const ALL_LAYERS = { stations: true, routes: true, noGoZones: true } as const;
const SNAP_METRES = 0.5;

function initialContent(): LayoutVersionContent {
  return layoutVersionContentSchema.parse({
    width: defaultFactoryLayout.width,
    height: defaultFactoryLayout.height,
    stations: defaultFactoryLayout.stations,
    routes: defaultFactoryLayout.routes.map((route) => ({
      ...route,
      start_station_id: route.start_station_id ?? "BATTERY_BUFFER",
      end_station_id: route.end_station_id ?? "MARRIAGE_STATION",
    })),
    no_go_zones: defaultFactoryLayout.no_go_zones,
    congestion_zones: [{
      id: "WAREHOUSE_PRODUCTION_DOOR",
      delay_multiplier: 1.25,
      points: [
        { x: 38, y: 17.5 },
        { x: 42, y: 17.5 },
        { x: 42, y: 22.5 },
        { x: 38, y: 22.5 },
      ],
    }],
    config: {
      robot_count: 5,
      demand_interval_seconds: 8,
      robot_speed_mps: 1.2,
      charger_count: 2,
    },
  });
}

function contentToMap(content: LayoutVersionContent, id: string, name: string, version: number) {
  return projectLayoutVersion({
    ...content,
    layout_id: id,
    name,
    version,
    created_by: "00000000-0000-4000-8000-000000000000",
    created_at: "2026-01-01T00:00:00Z",
    archived_at: null,
  });
}

function numberValue(value: string) {
  return Math.round(Number(value) / SNAP_METRES) * SNAP_METRES;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

/**
 * Route drawing has an order the map cannot express on its own, so the steps
 * are shown with live state instead of a transient one-line notice.
 */
function RouteStepper({
  route,
  placed,
}: {
  route: LayoutVersionContent["routes"][number];
  placed: number;
}) {
  const steps = [
    `Select ${route.start_station_id}`,
    placed > 1 ? `Add waypoints · ${placed - 1} placed` : "Add waypoints",
    `Select ${route.end_station_id}`,
  ];
  const current = placed === 0 ? 0 : 1;

  return (
    <ol className="route-stepper" aria-label={`Drawing ${route.id}`}>
      {steps.map((step, index) => (
        <li
          key={step}
          className={index < current ? "done" : index === current ? "current" : "pending"}
          aria-current={index === current ? "step" : undefined}
        >
          <b aria-hidden="true">{index + 1}</b>{step}
        </li>
      ))}
    </ol>
  );
}

/**
 * A candidate is not stored anywhere: the newest scenario benchmarked on this
 * exact layout version stands in for it, so the editor can say where the
 * revision currently sits in review without a new endpoint.
 */
function VersionCandidate({ layoutId, version }: { layoutId: string; version: number }) {
  const scenarios = useFactoryStore((state) => state.scenarios);
  const candidate = candidateForLayoutVersion(scenarios, layoutId, version);

  if (!candidate) {
    return <p className="form-help">
      Version {version} has not been simulated yet, so no Monitor can review it.
    </p>;
  }

  return <>
    <p className="form-help">
      Version {version} is represented by candidate <strong>{candidate.name}</strong>.
    </p>
    <WorkflowTimeline status={candidate.status}/>
  </>;
}

function LayoutWorkspace() {
  const { user } = useAuth();
  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [selected, setSelected] = useState<LayoutVersion | null>(null);
  const [name, setName] = useState("Battery logistics candidate");
  const [draft, setDraft] = useState<LayoutVersionContent>(initialContent);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [zoneError, setZoneError] = useState<string | null>(null);
  const [routeDrawing, setRouteDrawing] = useState(false);
  const [routeDraft, setRouteDraft] = useState<WorldPoint[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState("BATTERY_DELIVERY");
  const parsed = layoutVersionContentSchema.safeParse(draft);
  const preview = useMemo<FactoryLayout | null>(() => parsed.success
    ? contentToMap(
        parsed.data,
        selected?.layout_id ?? "LAYOUT-DRAFT",
        name,
        selected?.version ?? 1,
      )
    : null, [name, parsed, selected]);

  const refreshLayouts = useCallback(async () => {
    const loaded = await apiClient.getLayouts();
    setLayouts(loaded);
    return loaded;
  }, []);

  const loadLayout = useCallback(async (id: string) => {
    setBusy(true);
    setNotice(null);
    try {
      const loaded = await apiClient.getLayout(id);
      setSelected(loaded);
      setName(loaded.name);
      setDraft(layoutVersionContentSchema.parse(loaded));
      setSelectedRouteId(loaded.routes[0]?.id ?? "");
      setRouteDrawing(false);
      setRouteDraft([]);
    } catch (error) {
      setNotice(`Unable to load layout: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void refreshLayouts()
      .then((loaded) => loaded[0] ? loadLayout(loaded[0].id) : undefined)
      .catch((error: unknown) => setNotice(`Unable to load layouts: ${errorMessage(error)}`));
  }, [loadLayout, refreshLayouts]);

  if (!user) return null;
  if (!can(user.role, "layout:edit")) {
    return <section className="panel access-denied" role="alert">
      <div className="eyebrow">403 Forbidden</div>
      <h2>Designer access required</h2>
      <p>Only Designers can create and version factory layouts.</p>
    </section>;
  }

  function resetDraft() {
    setSelected(null);
    setName("Battery logistics candidate");
    setDraft(initialContent());
    setNotice(null);
    setZoneError(null);
    setRouteDrawing(false);
    setRouteDraft([]);
    setSelectedRouteId("BATTERY_DELIVERY");
  }

  function moveStation(id: string, point: WorldPoint) {
    setDraft((current) => ({
      ...current,
      stations: current.stations.map((station) => (
        station.id === id ? { ...station, ...point } : station
      )),
      routes: current.routes.map((route) => ({
        ...route,
        waypoints: route.waypoints.map((waypoint, index) => {
          if (index === 0 && route.start_station_id === id) return point;
          if (index === route.waypoints.length - 1 && route.end_station_id === id) return point;
          return waypoint;
        }),
      })),
    }));
  }

  function updateStation(id: string, field: "x" | "y", value: number) {
    const station = draft.stations.find((candidate) => candidate.id === id);
    if (station) moveStation(id, { x: station.x, y: station.y, [field]: value });
  }

  function startRouteDrawing() {
    const route = draft.routes.find((candidate) => candidate.id === selectedRouteId);
    if (!route) return;
    setRouteDrawing(true);
    setRouteDraft([]);
    setNotice(null);
  }

  function addRoutePoint(point: WorldPoint) {
    if (routeDraft.length === 0) {
      setNotice("Select the configured start station before adding waypoints.");
      return;
    }
    setRouteDraft((current) => [...current, point]);
  }

  function selectRouteStation(stationId: string) {
    const route = draft.routes.find((candidate) => candidate.id === selectedRouteId);
    const station = draft.stations.find((candidate) => candidate.id === stationId);
    if (!route || !station) return;
    if (routeDraft.length === 0) {
      if (stationId !== route.start_station_id) {
        setNotice(`Start at ${route.start_station_id}.`);
        return;
      }
      setRouteDraft([{ x: station.x, y: station.y }]);
      setNotice(null);
      return;
    }
    if (stationId !== route.end_station_id) {
      setNotice(`Finish at ${route.end_station_id}.`);
      return;
    }
    const waypoints = [...routeDraft, { x: station.x, y: station.y }];
    setDraft((current) => ({
      ...current,
      routes: current.routes.map((candidate) => (
        candidate.id === selectedRouteId ? { ...candidate, waypoints } : candidate
      )),
    }));
    setRouteDraft([]);
    setRouteDrawing(false);
    setNotice(`${route.id} updated. Save it as an immutable version.`);
  }

  function addRoute(kind: "DELIVERY" | "SUPPORT") {
    const start = draft.stations.find((station) => station.type === (
      kind === "DELIVERY" ? "BATTERY_BUFFER" : "CHARGING_STATION"
    ));
    const destinations = draft.stations.filter((station) => station.type === (
      kind === "DELIVERY" ? "MARRIAGE_STATION" : "BATTERY_BUFFER"
    ));
    if (!start || destinations.length === 0) return;
    const usedDestinations = new Set(
      draft.routes.filter((route) => route.kind === kind)
        .map((route) => route.end_station_id),
    );
    const end = destinations.find((station) => !usedDestinations.has(station.id))
      ?? destinations[0];
    const prefix = kind === "DELIVERY" ? "BATTERY_DELIVERY" : "SUPPORT_ROUTE";
    let suffix = draft.routes.filter((route) => route.kind === kind).length + 1;
    while (draft.routes.some((route) => route.id === `${prefix}_${suffix}`)) suffix += 1;
    const id = `${prefix}_${suffix}`;
    setDraft((current) => ({
      ...current,
      routes: [...current.routes, {
        id,
        kind,
        start_station_id: start.id,
        end_station_id: end.id,
        waypoints: [{ x: start.x, y: start.y }, { x: end.x, y: end.y }],
      }],
    }));
    setSelectedRouteId(id);
    setRouteDrawing(false);
    setRouteDraft([]);
    setNotice(`${id} added. Draw its safe path on the map.`);
  }

  function removeSelectedRoute() {
    const route = draft.routes.find((candidate) => candidate.id === selectedRouteId);
    if (!route) return;
    const remaining = draft.routes.filter((candidate) => candidate.id !== route.id);
    if (!remaining.some((candidate) => candidate.kind === "DELIVERY")) {
      setNotice("A layout must keep at least one delivery route.");
      return;
    }
    setDraft((current) => ({ ...current, routes: remaining }));
    setSelectedRouteId(remaining[0]?.id ?? "");
    setRouteDrawing(false);
    setRouteDraft([]);
    setNotice(`${route.id} removed from the draft.`);
  }

  function updateRouteEndpoint(
    routeIndex: number,
    field: "start_station_id" | "end_station_id",
    stationId: string,
  ) {
    const station = draft.stations.find((candidate) => candidate.id === stationId);
    if (!station) return;
    setDraft((current) => ({
      ...current,
      routes: current.routes.map((route, index) => {
        if (index !== routeIndex) return route;
        const waypointIndex = field === "start_station_id" ? 0 : route.waypoints.length - 1;
        return {
          ...route,
          [field]: stationId,
          waypoints: route.waypoints.map((point, pointIndex) => (
            pointIndex === waypointIndex ? { x: station.x, y: station.y } : point
          )),
        };
      }),
    }));
  }

  function updateWaypoint(routeIndex: number, pointIndex: number, field: "x" | "y", value: number) {
    setDraft((current) => ({
      ...current,
      routes: current.routes.map((route, currentRouteIndex) => currentRouteIndex === routeIndex
        ? {
            ...route,
            waypoints: route.waypoints.map((point, currentPointIndex) => (
              currentPointIndex === pointIndex ? { ...point, [field]: value } : point
            )),
          }
        : route),
    }));
  }

  function updateZones(field: "no_go_zones" | "congestion_zones", value: string) {
    try {
      const zones: unknown = JSON.parse(value);
      setDraft((current) => layoutVersionContentSchema.parse({ ...current, [field]: zones }));
      setZoneError(null);
    } catch (error) {
      setZoneError(`${field.replaceAll("_", " ")}: ${errorMessage(error)}`);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!parsed.success || zoneError) return;
    setBusy(true);
    setNotice(null);
    try {
      const creatingVersion = Boolean(selected);
      const saved = selected
        ? await apiClient.createLayoutVersion(selected.layout_id, { content: parsed.data })
        : await apiClient.createLayout({ name, content: parsed.data });
      setSelected(saved);
      setName(saved.name);
      setDraft(layoutVersionContentSchema.parse(saved));
      await refreshLayouts();
      setNotice(creatingVersion ? `Created immutable version ${saved.version}.` : `Created ${saved.layout_id}.`);
    } catch (error) {
      setNotice(`Unable to save layout: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function rename() {
    if (!selected) return;
    setBusy(true);
    try {
      const updated = await apiClient.renameLayout(selected.layout_id, name);
      setSelected(updated);
      await refreshLayouts();
      setNotice("Layout metadata renamed; immutable geometry was unchanged.");
    } catch (error) {
      setNotice(`Unable to rename layout: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    if (!selected || !window.confirm(`Archive ${selected.layout_id}?`)) return;
    setBusy(true);
    try {
      await apiClient.archiveLayout(selected.layout_id);
      resetDraft();
      await refreshLayouts();
      setNotice("Layout archived. Existing scenario references remain valid.");
    } catch (error) {
      setNotice(`Unable to archive layout: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const drawingRoute = draft.routes.find((route) => route.id === selectedRouteId);

  return <>
    <header className="page-head">
      <div><h2>Layout editor</h2><p>Create immutable factory geometry and runtime configuration.</p></div>
      <button className="button" type="button" onClick={resetDraft}>New layout</button>
    </header>

    <section className="panel scenario-queue">
      <div className="panel-head"><h3>Saved layouts</h3><span>{layouts.length} active</span></div>
      <div className="scenario-tabs" role="list" aria-label="Saved layouts">
        {layouts.map((layout) => <button key={layout.id} type="button"
          className={selected?.layout_id === layout.id ? "selected" : ""}
          onClick={() => void loadLayout(layout.id)}>
          <span>{layout.name}</span><small>{layout.id} · v{layout.latest_version}</small>
        </button>)}
      </div>
    </section>

    <div className="layout-editor-grid">
      <form className="panel layout-editor-form" onSubmit={save}>
        <div className="panel-head"><h3>Candidate geometry</h3><span>{SNAP_METRES} m grid</span></div>
        <div className="panel-body">
          <div className="form-grid">
            <div className="field field-wide"><label htmlFor="layout-name">Layout name</label>
              <input id="layout-name" value={name} onChange={(event) => setName(event.target.value)}/></div>
            <div className="field"><label htmlFor="layout-width">Factory width (m)</label>
              <input id="layout-width" type="number" min="1" step={SNAP_METRES} value={draft.width}
                onChange={(event) => setDraft({ ...draft, width: numberValue(event.target.value) })}/></div>
            <div className="field"><label htmlFor="layout-height">Factory height (m)</label>
              <input id="layout-height" type="number" min="1" step={SNAP_METRES} value={draft.height}
                onChange={(event) => setDraft({ ...draft, height: numberValue(event.target.value) })}/></div>
          </div>

          <h4 className="editor-section-title">Runtime configuration</h4>
          <div className="form-grid">
            {([
              ["robot_count", "Robot count", 1],
              ["demand_interval_seconds", "Demand interval (s)", 0.1],
              ["robot_speed_mps", "Robot speed (m/s)", 0.1],
              ["charger_count", "Charger count", 1],
            ] as const).map(([field, label, step]) => <div className="field" key={field}>
              <label htmlFor={`config-${field}`}>{label}</label>
              <input id={`config-${field}`} type="number" min={step} step={step}
                value={draft.config[field]}
                onChange={(event) => setDraft({
                  ...draft,
                  config: { ...draft.config, [field]: Number(event.target.value) },
                })}/>
            </div>)}
          </div>

          <h4 className="editor-section-title">Stations</h4>
          <div className="layout-editor-items">{draft.stations.map((station) => <fieldset key={station.id}>
            <legend>{station.type.replaceAll("_", " ")}</legend>
            <div className="form-grid">{(["x", "y"] as const).map((field) => <div className="field" key={field}>
              <label htmlFor={`${station.id}-${field}`}>{field.toUpperCase()} (m)</label>
              <input id={`${station.id}-${field}`} type="number" min="0" step={SNAP_METRES}
                value={station[field]}
                onChange={(event) => updateStation(station.id, field, numberValue(event.target.value))}/>
            </div>)}</div>
          </fieldset>)}</div>

          <h4 className="editor-section-title">Routes</h4>
          <div className="button-row layout-route-tools">
            <button className="button" type="button" onClick={() => addRoute("DELIVERY")}>
              Add delivery route
            </button>
            <button className="button" type="button" onClick={() => addRoute("SUPPORT")}>
              Add support route
            </button>
            <button className="button" type="button" onClick={startRouteDrawing}>
              {routeDrawing ? "Restart selected route" : "Draw selected route"}
            </button>
            <button className="button danger" type="button" onClick={removeSelectedRoute}>
              Remove selected route
            </button>
            {routeDrawing && <button className="button" type="button" onClick={() => {
              setRouteDrawing(false);
              setRouteDraft([]);
              setNotice(null);
            }}>Cancel drawing</button>}
          </div>
          {routeDrawing && drawingRoute
            && <RouteStepper route={drawingRoute} placed={routeDraft.length}/>}
          <div className="layout-editor-items">{draft.routes.map((route, routeIndex) => <fieldset
            key={route.id} className={route.id === selectedRouteId ? "selected-route" : ""}
            onClick={() => setSelectedRouteId(route.id)}
          >
            <legend><label>
              <input type="radio" name="selected-route" value={route.id}
                checked={route.id === selectedRouteId}
                onChange={() => setSelectedRouteId(route.id)}/>
              {route.id} · {route.kind}
            </label></legend>
            <div className="form-grid route-endpoints">
              {(["start_station_id", "end_station_id"] as const).map((field) => <div
                className="field" key={field}
              >
                <label htmlFor={`${route.id}-${field}`}>{field === "start_station_id" ? "Start" : "End"}</label>
                <select id={`${route.id}-${field}`} value={route[field]}
                  onChange={(event) => updateRouteEndpoint(routeIndex, field, event.target.value)}>
                  {draft.stations.map((station) => <option key={station.id} value={station.id}>
                    {station.id}
                  </option>)}
                </select>
              </div>)}
            </div>
            <div className="waypoint-list">{route.waypoints.map((point, pointIndex) => <div className="waypoint-row" key={`${route.id}-${pointIndex}`}>
              <strong>#{pointIndex + 1}</strong>
              {(["x", "y"] as const).map((field) => <label key={field}><span>{field.toUpperCase()}</span>
                <input aria-label={`${route.id} waypoint ${pointIndex + 1} ${field.toUpperCase()}`}
                  type="number" min="0" step={SNAP_METRES} value={point[field]}
                  onChange={(event) => updateWaypoint(routeIndex, pointIndex, field, numberValue(event.target.value))}/>
              </label>)}
            </div>)}</div>
          </fieldset>)}</div>

          <h4 className="editor-section-title">Zones (JSON)</h4>
          <div className="field"><label htmlFor="no-go-zones">No-go zones</label>
            <textarea id="no-go-zones" rows={5} key={`no-go-${selected?.layout_id}-${selected?.version}`}
              defaultValue={JSON.stringify(draft.no_go_zones, null, 2)}
              onBlur={(event) => updateZones("no_go_zones", event.target.value)}/></div>
          <div className="field"><label htmlFor="congestion-zones">Congestion zones</label>
            <textarea id="congestion-zones" rows={5} key={`congestion-${selected?.layout_id}-${selected?.version}`}
              defaultValue={JSON.stringify(draft.congestion_zones, null, 2)}
              onBlur={(event) => updateZones("congestion_zones", event.target.value)}/></div>

          {(zoneError || !parsed.success) && <div className="scenario-error" role="alert">
            {zoneError ?? parsed.error?.issues[0]?.message ?? "Layout is invalid."}
          </div>}
          {notice && <div className="review-note" role="status">{notice}</div>}
          <p className="form-help">
            Saving stores an immutable revision. The live factory keeps running its current layout
            until a Monitor applies a simulated candidate built on this revision.
          </p>
          {selected && <VersionCandidate layoutId={selected.layout_id} version={selected.version}/>}
          <div className="button-row">
            {selected && <button className="button" type="button" disabled={busy} onClick={() => void rename()}>Rename</button>}
            {selected && <button className="button" type="button" disabled={busy} onClick={() => void archive()}>Archive</button>}
            <button className="button primary" type="submit" disabled={busy || !parsed.success || Boolean(zoneError)}>
              {busy ? "Saving…" : selected ? "Save candidate revision" : "Create layout"}
            </button>
            {selected && <a className="button primary" href={`/scenarios?layout=${encodeURIComponent(selected.layout_id)}&version=${selected.version}`}>
              Simulate this version
            </a>}
          </div>
        </div>
      </form>

      <section className="panel layout-preview-panel">
        <div className="panel-head"><h3>Live 2D preview</h3><span>{preview ? "Valid candidate" : "Fix validation errors"}</span></div>
        <div className="layout-preview">{preview
          ? <FactoryPlantMap2D
              robots={[]} selectedRobotId={null} onSelect={() => undefined}
              layers={ALL_LAYERS} layout={preview}
              editor={{
                routeDrawing,
                routeDraft,
                selectedRouteId,
                onStationMove: moveStation,
                onRoutePoint: addRoutePoint,
                onRouteStation: selectRouteStation,
              }}
            />
          : <div className="empty">Preview pauses while the draft is invalid.</div>}
        </div>
      </section>
    </div>
  </>;
}

export default function LayoutsPage() {
  return <LayoutWorkspace/>;
}
