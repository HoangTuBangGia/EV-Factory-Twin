"use client";

import { useFactoryStore } from "@/stores/factory-store";

function PauseIcon({ paused }: { paused: boolean }) {
  return paused
    ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z"/></svg>
    : <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14M16 5v14"/></svg>;
}

export function LivePauseButton({ cockpit = false }: { cockpit?: boolean }) {
  const paused = useFactoryStore((state) => state.paused);
  const togglePaused = useFactoryStore((state) => state.togglePaused);
  const label = paused ? "Resume live updates" : "Pause live updates";

  return (
    <button
      className={cockpit
        ? `cockpit-tool-button live-pause${paused ? " paused" : ""}`
        : `button compact live-pause${paused ? " paused" : ""}`}
      type="button"
      aria-label={label}
      aria-pressed={paused}
      title={label}
      onClick={togglePaused}
    >
      <PauseIcon paused={paused}/>
      {!cockpit && <span>{paused ? "PAUSED" : "Pause"}</span>}
    </button>
  );
}
