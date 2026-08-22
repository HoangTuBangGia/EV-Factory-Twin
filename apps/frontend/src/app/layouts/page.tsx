"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { FactoryMap2D } from "@/components/factory/factory-map-2d";
import { can } from "@/lib/auth/permissions";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import {
  factoryLayoutSchema,
  type FactoryLayout,
  type FactoryStation,
} from "@/schemas/factory";

const ALL_LAYERS = { stations: true, routes: true, noGoZones: true } as const;
const SNAP_METRES = 0.5;

function cloneDefaultLayout(): FactoryLayout {
  return structuredClone(defaultFactoryLayout);
}

function numberValue(value: string) {
  return Math.round(Number(value) / SNAP_METRES) * SNAP_METRES;
}

export default function LayoutsPage() {
  const { user } = useAuth();
  const [draft, setDraft] = useState<FactoryLayout>(cloneDefaultLayout);
  const parsed = factoryLayoutSchema.safeParse(draft);

  if (!user) return null;
  if (!can(user.role, "layout:edit")) {
    return <section className="panel access-denied" role="alert">
      <div className="eyebrow">403 Forbidden</div>
      <h2>Designer access required</h2>
      <p>Only Designers can prepare factory layout candidates.</p>
    </section>;
  }

  function updateSize(field: "width" | "height", value: number) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function updateStation(id: string, field: "x" | "y", value: number) {
    setDraft((current) => ({
      ...current,
      stations: current.stations.map((station) => (
        station.id === id ? { ...station, [field]: value } : station
      )),
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

  function addWaypoint(routeIndex: number) {
    setDraft((current) => ({
      ...current,
      routes: current.routes.map((route, currentRouteIndex) => {
        if (currentRouteIndex !== routeIndex) return route;
        const previous = route.waypoints.at(-1) ?? { x: 0, y: 0 };
        return { ...route, waypoints: [...route.waypoints, { ...previous }] };
      }),
    }));
  }

  function removeWaypoint(routeIndex: number, pointIndex: number) {
    setDraft((current) => ({
      ...current,
      routes: current.routes.map((route, currentRouteIndex) => currentRouteIndex === routeIndex
        ? { ...route, waypoints: route.waypoints.filter((_, index) => index !== pointIndex) }
        : route),
    }));
  }

  return <>
    <header className="page-head">
      <div>
        <h2>Layout editor</h2>
        <p>Prepare a validated 2D candidate before simulation and Monitor approval.</p>
      </div>
      <button className="button" type="button" onClick={() => setDraft(cloneDefaultLayout())}>
        Reset draft
      </button>
    </header>

    <div className="layout-editor-grid">
      <section className="panel layout-editor-form">
        <div className="panel-head">
          <h3>Candidate geometry</h3>
          <span>{SNAP_METRES} m grid</span>
        </div>
        <div className="panel-body">
          <div className="form-grid">
            <div className="field">
              <label htmlFor="layout-width">Factory width (m)</label>
              <input id="layout-width" type="number" min="1" step={SNAP_METRES} value={draft.width}
                onChange={(event) => updateSize("width", numberValue(event.target.value))}/>
            </div>
            <div className="field">
              <label htmlFor="layout-height">Factory height (m)</label>
              <input id="layout-height" type="number" min="1" step={SNAP_METRES} value={draft.height}
                onChange={(event) => updateSize("height", numberValue(event.target.value))}/>
            </div>
          </div>

          <h4 className="editor-section-title">Stations</h4>
          <div className="layout-editor-items">
            {draft.stations.map((station: FactoryStation) => <fieldset key={station.id}>
              <legend>{station.type.replaceAll("_", " ")}</legend>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor={`${station.id}-x`}>X (m)</label>
                  <input id={`${station.id}-x`} type="number" min="0" max={draft.width}
                    step={SNAP_METRES} value={station.x}
                    onChange={(event) => updateStation(station.id, "x", numberValue(event.target.value))}/>
                </div>
                <div className="field">
                  <label htmlFor={`${station.id}-y`}>Y (m)</label>
                  <input id={`${station.id}-y`} type="number" min="0" max={draft.height}
                    step={SNAP_METRES} value={station.y}
                    onChange={(event) => updateStation(station.id, "y", numberValue(event.target.value))}/>
                </div>
              </div>
            </fieldset>)}
          </div>

          <h4 className="editor-section-title">Routes</h4>
          <div className="layout-editor-items">
            {draft.routes.map((route, routeIndex) => <fieldset key={route.id}>
              <legend>{route.id}</legend>
              <div className="waypoint-list">
                {route.waypoints.map((point, pointIndex) => <div className="waypoint-row" key={`${route.id}-${pointIndex}`}>
                  <strong>#{pointIndex + 1}</strong>
                  <label>
                    <span>X</span>
                    <input aria-label={`${route.id} waypoint ${pointIndex + 1} X`} type="number"
                      min="0" max={draft.width} step={SNAP_METRES} value={point.x}
                      onChange={(event) => updateWaypoint(routeIndex, pointIndex, "x", numberValue(event.target.value))}/>
                  </label>
                  <label>
                    <span>Y</span>
                    <input aria-label={`${route.id} waypoint ${pointIndex + 1} Y`} type="number"
                      min="0" max={draft.height} step={SNAP_METRES} value={point.y}
                      onChange={(event) => updateWaypoint(routeIndex, pointIndex, "y", numberValue(event.target.value))}/>
                  </label>
                  <button className="button compact" type="button" disabled={route.waypoints.length <= 2}
                    aria-label={`Remove ${route.id} waypoint ${pointIndex + 1}`}
                    onClick={() => removeWaypoint(routeIndex, pointIndex)}>Remove</button>
                </div>)}
              </div>
              <button className="button compact" type="button" onClick={() => addWaypoint(routeIndex)}>
                Add waypoint
              </button>
            </fieldset>)}
          </div>

          {!parsed.success && <div className="scenario-error" role="alert">
            {parsed.error.issues[0]?.message ?? "Layout is invalid."}
          </div>}
          <p className="form-help">
            Draft-only preview. Saving/versioning remains disabled until the backend layout API exists.
          </p>
        </div>
      </section>

      <section className="panel layout-preview-panel">
        <div className="panel-head">
          <h3>Live 2D preview</h3>
          <span>{parsed.success ? "Valid candidate" : "Fix validation errors"}</span>
        </div>
        <div className="layout-preview">
          {parsed.success
            ? <FactoryMap2D robots={[]} selectedRobotId={null} onSelect={() => undefined}
                layers={ALL_LAYERS} layout={parsed.data}/>
            : <div className="empty">Preview pauses while the draft is invalid.</div>}
        </div>
      </section>
    </div>
  </>;
}
