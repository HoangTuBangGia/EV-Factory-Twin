import type { LayoutVersionContent } from "@/schemas/layout";

export type ZoneKind = "no_go_zones" | "congestion_zones";

export interface ZoneSelection {
  kind: ZoneKind;
  index: number;
}

export interface ZoneDrawing {
  kind: ZoneKind;
  id: string;
  points: LayoutVersionContent["no_go_zones"][number]["points"];
}

export function LayoutZoneEditor({
  content,
  selection,
  drawing,
  onSelect,
  onBegin,
  onUpdateId,
  onUpdateDelay,
  onUpdatePoint,
  onRemove,
  onUndo,
  onCancel,
  onFinish,
}: {
  content: LayoutVersionContent;
  selection: ZoneSelection | null;
  drawing: ZoneDrawing | null;
  onSelect: (selection: ZoneSelection) => void;
  onBegin: (kind: ZoneKind) => void;
  onUpdateId: (selection: ZoneSelection, id: string) => void;
  onUpdateDelay: (selection: ZoneSelection, value: number) => void;
  onUpdatePoint: (
    selection: ZoneSelection,
    pointIndex: number,
    field: "x" | "y",
    value: number,
  ) => void;
  onRemove: (selection: ZoneSelection) => void;
  onUndo: () => void;
  onCancel: () => void;
  onFinish: () => void;
}) {
  const groups = [
    ["no_go_zones", "No-go zones"] as const,
    ["congestion_zones", "Congestion zones"] as const,
  ];

  return <>
    <div className="button-row layout-zone-tools">
      <button className="button" type="button" disabled={Boolean(drawing)}
        onClick={() => onBegin("no_go_zones")}>Add no-go zone</button>
      <button className="button" type="button" disabled={Boolean(drawing)}
        onClick={() => onBegin("congestion_zones")}>Add congestion zone</button>
    </div>

    {drawing && <section className="zone-drawing-guide" aria-label="Zone drawing progress">
      <strong>Drawing {drawing.id}</strong>
      <span>Click at least three boundary points on the 2D map · {drawing.points.length} placed</span>
      <div className="button-row">
        <button className="button" type="button" disabled={drawing.points.length === 0}
          onClick={onUndo}>Undo last point</button>
        <button className="button" type="button" onClick={onCancel}>Cancel drawing</button>
        <button className="button primary" type="button" disabled={drawing.points.length < 3}
          onClick={onFinish}>Finish zone</button>
      </div>
    </section>}

    {groups.map(([kind, label]) => <section className="zone-group" key={kind}>
      <div className="zone-group-head"><h5>{label}</h5><span>{content[kind].length}</span></div>
      {content[kind].length === 0 && <p className="form-help">No {label.toLowerCase()} configured.</p>}
      <div className="layout-editor-items">{content[kind].map((zone, index) => {
        const current = { kind, index };
        const selected = selection?.kind === kind && selection.index === index;
        return <fieldset key={`${kind}-${index}`} className={selected ? "selected-zone" : ""}
          onClick={() => onSelect(current)}>
          <legend><label>
            <input type="radio" name="selected-zone" checked={selected}
              aria-label={`Select zone ${zone.id}`} onChange={() => onSelect(current)}/>
            {zone.id}
          </label></legend>
          <div className="form-grid zone-metadata">
            <div className="field"><label htmlFor={`${kind}-${index}-id`}>Zone ID</label>
              <input id={`${kind}-${index}-id`} value={zone.id}
                onChange={(event) => onUpdateId(current, event.target.value.toUpperCase())}/></div>
            {kind === "congestion_zones" && <div className="field">
              <label htmlFor={`${kind}-${index}-delay`}>Delay multiplier</label>
              <input id={`${kind}-${index}-delay`} type="number" min="1" max="10" step="0.05"
                value={"delay_multiplier" in zone ? zone.delay_multiplier : 1}
                onChange={(event) => onUpdateDelay(current, Number(event.target.value))}/>
            </div>}
          </div>
          <div className="waypoint-list">{zone.points.map((point, pointIndex) => <div
            className="waypoint-row" key={`${zone.id}-${pointIndex}`}>
            <strong>#{pointIndex + 1}</strong>
            {(["x", "y"] as const).map((field) => <label key={field}>
              <span>{field.toUpperCase()} (m)</span>
              <input aria-label={`${zone.id} point ${pointIndex + 1} ${field.toUpperCase()}`}
                type="number" min="0" step="0.5" value={point[field]}
                onChange={(event) => onUpdatePoint(
                  current,
                  pointIndex,
                  field,
                  Number(event.target.value),
                )}/>
            </label>)}
          </div>)}</div>
          <button className="button danger" type="button" onClick={() => onRemove(current)}>
            Delete zone
          </button>
        </fieldset>;
      })}</div>
    </section>)}
  </>;
}
