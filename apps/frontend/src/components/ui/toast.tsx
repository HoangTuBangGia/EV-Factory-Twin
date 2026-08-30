"use client";

import { useEffect, useRef } from "react";
import { useToastStore, getAutoDismissMs } from "@/stores/toast-store";
import type { ToastType } from "@/stores/toast-store";

const ROLE: Record<ToastType, string> = {
  success: "status",
  info: "status",
  error: "alert",
};

function ToastItem({ id, type, message }: { id: string; type: ToastType; message: string }) {
  const removeToast = useToastStore((s) => s.removeToast);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const ms = getAutoDismissMs(type);
    if (ms > 0) {
      timerRef.current = setTimeout(() => removeToast(id), ms);
      return () => { if (timerRef.current) clearTimeout(timerRef.current); };
    }
  }, [id, type, removeToast]);

  return (
    <div
      className={`toast toast-${type}`}
      role={ROLE[type]}
      aria-live={type === "error" ? "assertive" : "polite"}
    >
      <span className="toast-message">{message}</span>
      <button
        className="toast-close"
        type="button"
        aria-label="Dismiss"
        onClick={() => removeToast(id)}
      >
        ×
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-label="Notifications">
      {toasts.map((t) => (
        <ToastItem key={t.id} id={t.id} type={t.type} message={t.message} />
      ))}
    </div>
  );
}
