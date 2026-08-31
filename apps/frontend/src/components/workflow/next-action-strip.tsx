"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { apiClient } from "@/lib/api-client";
import { nextAction } from "@/lib/workflow";
import { useFactoryStore } from "@/stores/factory-store";

/**
 * Role-aware answer to "what do I do next?". It lives in the application frame
 * so the same guidance is available on every route, and it doubles as the
 * Monitor's review inbox pointer.
 */
export function NextActionStrip({ floating = false }: { floating?: boolean }) {
  const { user } = useAuth();
  const scenarios = useFactoryStore((state) => state.scenarios);
  const setScenarios = useFactoryStore((state) => state.setScenarios);
  const factoryRevision = useFactoryStore((state) => state.factoryRevision);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    if (!user) return;
    let active = true;
    apiClient.getScenarios()
      .then((loaded) => {
        if (!active) return;
        setScenarios(loaded);
        setState("ready");
      })
      .catch(() => {
        // Guidance is advisory: an unreachable API hides the strip instead of
        // breaking the frame around it.
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [factoryRevision, setScenarios, user]);

  if (!user || state !== "ready") return null;
  const action = nextAction(user.role, scenarios, user.id);

  return (
    <aside className={`workflow-strip${floating ? " floating" : ""}`} aria-label="Next step">
      <div>
        <span className="eyebrow">Next step</span>
        <strong>{action.headline}</strong>
        <p>{action.hint}</p>
      </div>
      {action.cta && (
        <Link className="button" href={action.cta.href}>{action.cta.label}</Link>
      )}
    </aside>
  );
}
