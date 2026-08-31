"use client";

import { type ReactNode, useId, useRef, useState } from "react";

export function Tooltip({
  content,
  label,
  contentId,
}: {
  content: ReactNode;
  label: string;
  contentId?: string;
}) {
  const generatedId = useId();
  const id = contentId ?? generatedId;
  const [pinned, setPinned] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  function dismiss() {
    setPinned(false);
    triggerRef.current?.blur();
  }

  return <span className={`tooltip${pinned ? " open" : ""}`}>
    <button
      ref={triggerRef}
      className="tooltip-trigger"
      type="button"
      aria-label={label}
      aria-describedby={id}
      aria-expanded={pinned}
      onClick={() => pinned ? dismiss() : setPinned(true)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          dismiss();
        }
      }}
    >ⓘ</button>
    <span className="tooltip-content" id={id} role="tooltip">{content}</span>
  </span>;
}
