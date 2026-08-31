import { z } from "zod";
import { scenarioSchema } from "./scenario";

export const layoutCandidateSchema = z.object({
  layout_id: z.string().min(1).max(80),
  layout_version: z.number().int().min(1),
});

interface OptimizationDimensions {
  layouts: unknown[];
  route_ids: unknown[];
  robot_counts: unknown[];
  robot_speeds_mps: unknown[];
  charger_counts: unknown[];
  demand_intervals: unknown[];
}

export function optimizationCandidateCount(request: OptimizationDimensions) {
  return [
    request.layouts,
    request.route_ids,
    request.robot_counts,
    request.robot_speeds_mps,
    request.charger_counts,
    request.demand_intervals,
  ].reduce((count, dimension) => count * dimension.length, 1);
}

export const optimizationRequestSchema = z.object({
  name_prefix: z.string().trim().min(1).max(50),
  layouts: z.array(layoutCandidateSchema).min(1).max(8),
  route_ids: z.array(z.string().min(1).max(80)).min(1).max(8),
  robot_counts: z.array(z.number().int().min(1).max(10)).min(1).max(8),
  robot_speeds_mps: z.array(z.number().positive().max(10)).min(1).max(8),
  charger_counts: z.array(z.number().int().min(1).max(20)).min(1).max(8),
  demand_intervals: z.array(z.number().min(1).max(60)).min(1).max(8),
  num_tasks: z.number().int().min(1).max(10_000).default(100),
  loading_time: z.number().positive().max(86_400).default(5),
  simulation_time: z.number().positive().max(86_400).default(3_600),
}).superRefine((request, context) => {
  const candidates = optimizationCandidateCount(request);
  if (candidates > 64) {
    context.addIssue({ code: "custom", message: "Optimization is limited to 64 candidates" });
  }
});

export const rankedScenarioSchema = z.object({
  rank: z.number().int().min(1),
  scenario: scenarioSchema,
});

export const optimizationResultSchema = z.object({
  evaluated_candidates: z.number().int().min(1).max(64),
  recommendation: scenarioSchema,
  ranking: z.array(rankedScenarioSchema),
});

export type OptimizationRequest = z.input<typeof optimizationRequestSchema>;
export type OptimizationResult = z.infer<typeof optimizationResultSchema>;
