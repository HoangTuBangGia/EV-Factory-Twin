import { z } from "zod";
import { factoryMetricsSchema } from "./metric";

export const kpiHistoryItemSchema = z.object({
  recorded_at: z.string().datetime({ offset: true }),
  simulated_elapsed_seconds: z.number().nonnegative(),
  metrics: factoryMetricsSchema,
  scenario_id: z.string().nullable(),
});

export const kpiHistoryPageSchema = z.object({
  items: z.array(kpiHistoryItemSchema),
  next_offset: z.number().int().nonnegative().nullable(),
});

export type KpiHistoryPage = z.infer<typeof kpiHistoryPageSchema>;
