"use client";

import { useEffect, useState } from "react";
import { FactoryPlantMap2D } from "@/components/factory/factory-plant-map-2d";
import { apiClient } from "@/lib/api-client";
import { diffLayoutContent } from "@/lib/layout-diff";
import { latestAppliedScenario, projectLayoutVersion } from "@/lib/layout-projection";
import type { LayoutVersion } from "@/schemas/layout";
import type { Scenario } from "@/schemas/scenario";
import { useFactoryStore } from "@/stores/factory-store";

const ALL_LAYERS = { stations: true, routes: true, noGoZones: true } as const;

function MapFrame({ caption, version }: { caption: string; version: LayoutVersion }) {
  return (
    <figure className="layout-comparison-map">
      <figcaption>{caption}</figcaption>
      <FactoryPlantMap2D
        robots={[]} selectedRobotId={null} onSelect={() => undefined}
        layers={ALL_LAYERS} layout={projectLayoutVersion(version)}
      />
    </figure>
  );
}

function ChangeList({ current, candidate }: { current: LayoutVersion; candidate: LayoutVersion }) {
  const changes = diffLayoutContent(current, candidate);
  if (changes.length === 0) {
    return <p className="form-help">
      Geometry and runtime configuration are identical; this revision changed metadata only.
    </p>;
  }

  return (
    <ul className="layout-changes">
      {changes.map((change) => (
        <li key={`${change.label}-${change.detail}`}>
          <strong>{change.label}</strong><span>{change.detail}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Physical context for a review decision: KPI deltas say a candidate is better,
 * not what moved. Both revisions are fetched lazily on expand so an unopened
 * panel costs nothing.
 */
export function LayoutComparison({ candidate }: { candidate: Scenario }) {
  const scenarios = useFactoryStore((state) => state.scenarios);
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<LayoutVersion | null>(null);
  const [proposed, setProposed] = useState<LayoutVersion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applied = latestAppliedScenario(scenarios);
  const live = applied && applied.id !== candidate.id ? applied.config : null;
  const { layout_id: layoutId, layout_version: version } = candidate.config;
  const reusesLive = live?.layout_id === layoutId && live?.layout_version === version;
  const liveId = reusesLive ? null : live?.layout_id ?? null;
  const liveVersion = reusesLive ? null : live?.layout_version ?? null;

  useEffect(() => {
    if (!open) return;
    let active = true;
    setError(null);
    setCurrent(null);
    setProposed(null);
    Promise.all([
      liveId && liveVersion ? apiClient.getLayoutVersion(liveId, liveVersion) : null,
      apiClient.getLayoutVersion(layoutId, version),
    ])
      .then(([loadedCurrent, loadedProposed]) => {
        if (!active) return;
        setCurrent(loadedCurrent);
        setProposed(loadedProposed);
      })
      .catch(() => {
        if (active) setError("Layout geometry is unavailable for this comparison.");
      });
    return () => { active = false; };
  }, [layoutId, liveId, liveVersion, open, version]);

  const summary = !live
    ? `Layout geometry · ${layoutId} v${version}`
    : reusesLive
      ? "Layout geometry · unchanged from the live factory"
      : `Layout change · ${live.layout_id} v${live.layout_version} → ${layoutId} v${version}`;

  return (
    <details
      className="layout-comparison"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>{summary}</summary>
      {error && <p className="notice">{error}</p>}
      {!error && !proposed && <p className="form-help">Loading layout geometry…</p>}
      {proposed && (
        <>
          {!live && <p className="form-help">
            No candidate has been applied yet, so the live factory still runs the seeded default
            layout and there is nothing to compare against.
          </p>}
          {reusesLive && <p className="form-help">
            This candidate reuses the live geometry; only simulation parameters differ.
          </p>}
          <div className="layout-comparison-maps">
            {current && <MapFrame
              caption={`Live factory · ${current.layout_id} v${current.version}`}
              version={current}
            />}
            <MapFrame caption={`Candidate · ${layoutId} v${version}`} version={proposed}/>
          </div>
          {current && <ChangeList current={current} candidate={proposed}/>}
        </>
      )}
    </details>
  );
}
