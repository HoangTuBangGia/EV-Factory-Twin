"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { latestAppliedScenario, projectLayoutVersion } from "@/lib/layout-projection";
import type { FactoryLayout } from "@/schemas/factory";
import { useFactoryStore } from "@/stores/factory-store";

export function useAppliedFactoryLayout(): FactoryLayout {
  const [layout, setLayout] = useState<FactoryLayout>(defaultFactoryLayout);
  const factoryRevision = useFactoryStore((state) => state.factoryRevision);

  useEffect(() => {
    let active = true;
    void apiClient.getScenarios()
      .then(async (scenarios) => {
        const applied = latestAppliedScenario(scenarios);
        if (!applied) return;
        const version = await apiClient.getLayoutVersion(
          applied.config.layout_id,
          applied.config.layout_version,
        );
        if (active) setLayout(projectLayoutVersion(version));
      })
      .catch(() => {
        // Live telemetry remains usable with the documented default layout.
      });
    return () => { active = false; };
  }, [factoryRevision]);

  return layout;
}
