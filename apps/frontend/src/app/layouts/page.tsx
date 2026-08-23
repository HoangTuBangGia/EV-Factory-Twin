"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { FactoryMap2D } from "@/components/factory/factory-map-2d";
import { apiClient } from "@/lib/api-client";
import { can } from "@/lib/auth/permissions";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { projectLayoutVersion } from "@/lib/layout-projection";
import type { FactoryLayout } from "@/schemas/factory";
import {
  layoutVersionContentSchema,
  type LayoutSummary,
  type LayoutVersion,
  type LayoutVersionContent,
} from "@/schemas/layout";

const ALL_LAYERS = { stations: true, routes: true, noGoZones: true } as const;
const SNAP_METRES = 0.5;

function initialContent(): LayoutVersionContent {
  return layoutVersionContentSchema.parse({
    width: defaultFactoryLayout.width,
    height: defaultFactoryLayout.height,
    stations: defaultFactoryLayout.stations,
    routes: defaultFactoryLayout.routes.map((route) => ({
      ...route,
      start_station_id: "BATTERY_BUFFER",
      end_station_id: "MARRIAGE_STATION",
    })),
    no_go_zones: defaultFactoryLayout.no_go_zones,
    congestion_zones: [],
    config: {
      robot_count: 2,
      demand_interval_seconds: 5,
      robot_speed_mps: 1,
      charger_count: 1,
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

export default function LayoutsPage() {
  const { user } = useAuth();
  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [selected, setSelected] = useState<LayoutVersion | null>(null);
  const [name, setName] = useState("Battery logistics candidate");
  const [draft, setDraft] = useState<LayoutVersionContent>(initialContent);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [zoneError, setZoneError] = useState<string | null>(null);
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
          <div className="layout-editor-items">{draft.routes.map((route, routeIndex) => <fieldset key={route.id}>
            <legend>{route.id} · {route.start_station_id} → {route.end_station_id}</legend>
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
          <div className="button-row">
            {selected && <button className="button" type="button" disabled={busy} onClick={() => void rename()}>Rename</button>}
            {selected && <button className="button" type="button" disabled={busy} onClick={() => void archive()}>Archive</button>}
            <button className="button primary" type="submit" disabled={busy || !parsed.success || Boolean(zoneError)}>
              {busy ? "Saving…" : selected ? "Create new version" : "Create layout"}
            </button>
          </div>
        </div>
      </form>

      <section className="panel layout-preview-panel">
        <div className="panel-head"><h3>Live 2D preview</h3><span>{preview ? "Valid candidate" : "Fix validation errors"}</span></div>
        <div className="layout-preview">{preview
          ? <FactoryMap2D robots={[]} selectedRobotId={null} onSelect={() => undefined} layers={ALL_LAYERS} layout={preview}/>
          : <div className="empty">Preview pauses while the draft is invalid.</div>}
        </div>
      </section>
    </div>
  </>;
}
