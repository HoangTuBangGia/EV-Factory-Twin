import { z } from "zod";
import { env } from "./env";
import { factoryAlertSchema } from "@/schemas/alert";
import { factoryMetricsSchema } from "@/schemas/metric";
import { mockFactoryConfigSchema, type MockFactoryConfig } from "@/schemas/factory";
import { robotSchema } from "@/schemas/robot";
import {
  scenarioRunRequestSchema,
  scenarioSchema,
  type ScenarioRunRequest,
} from "@/schemas/scenario";
import { taskSchema } from "@/schemas/task";

async function responseError(response: Response, path: string): Promise<Error> {
  try {
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "string") return new Error(detail);
    }
  } catch {
    // Fall back to the status-based message when the server did not return JSON.
  }
  return new Error(`API ${response.status}: ${path}`);
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw await responseError(response, path);
  return schema.parse(await response.json());
}

export const apiClient = {
  getFactory: () => request("/api/v1/factory", z.unknown()),
  getRobots: () => request("/api/v1/robots", z.array(robotSchema)),
  getRobot: (id: string) => request(`/api/v1/robots/${encodeURIComponent(id)}`, robotSchema),
  getTasks: () => request("/api/v1/tasks", z.array(taskSchema)),
  getTask: (id: string) => request(`/api/v1/tasks/${encodeURIComponent(id)}`, taskSchema),
  getMetrics: () => request("/api/v1/metrics", factoryMetricsSchema),
  getAlerts: () => request("/api/v1/alerts", z.array(factoryAlertSchema)),
  updateMockConfig: (config: MockFactoryConfig) =>
    request("/api/v1/mock/config", mockFactoryConfigSchema, {
      method: "POST",
      body: JSON.stringify(config),
    }),
  resetMockFactory: () => request("/api/v1/mock/reset", z.unknown(), { method: "POST" }),
  getBaselineScenario: () => request("/api/v1/scenarios/baseline", scenarioSchema),
  runScenario: (input: ScenarioRunRequest) =>
    request("/api/v1/scenarios/run", scenarioSchema, {
      method: "POST",
      body: JSON.stringify(scenarioRunRequestSchema.parse(input)),
    }),
  approveScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/approve`, scenarioSchema, {
      method: "POST",
    }),
  rejectScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/reject`, scenarioSchema, {
      method: "POST",
    }),
  applyScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/apply`, scenarioSchema, {
      method: "POST",
    }),
};
