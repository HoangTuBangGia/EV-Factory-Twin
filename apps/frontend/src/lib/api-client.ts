import { z } from "zod";
import { env } from "./env";
import { factoryAlertSchema } from "@/schemas/alert";
import { factoryMetricsSchema } from "@/schemas/metric";
import { robotSchema } from "@/schemas/robot";
import { taskSchema } from "@/schemas/task";

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(`API ${response.status}: ${path}`);
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
  updateMockConfig: (config: Record<string, number | string>) =>
    request("/api/v1/mock/speed", z.unknown(), { method: "POST", body: JSON.stringify(config) }),
  resetMockFactory: () => request("/api/v1/mock/reset", z.unknown(), { method: "POST" }),
};
