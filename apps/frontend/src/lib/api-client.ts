import { z } from "zod";
import { env } from "./env";
import { factoryAlertSchema } from "@/schemas/alert";
import {
  adminInviteRequestSchema,
  adminUserSchema,
  adminUserUpdateSchema,
  auditEventSchema,
  type AdminInviteRequest,
  type AdminUserUpdate,
} from "@/schemas/admin";
import { currentUserSchema } from "@/schemas/auth";
import { factoryMetricsSchema } from "@/schemas/metric";
import { mockFactoryConfigSchema, type MockFactoryConfig } from "@/schemas/factory";
import { robotSchema } from "@/schemas/robot";
import {
  scenarioRunRequestSchema,
  scenarioSchema,
  type ScenarioRunRequest,
} from "@/schemas/scenario";
import { taskSchema } from "@/schemas/task";

let accessToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export function setApiAccessToken(token: string | null) {
  accessToken = token;
}

export function setApiUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

async function responseError(response: Response, path: string): Promise<ApiError> {
  let detail = `API ${response.status}: ${path}`;
  try {
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      const responseDetail = (payload as { detail: unknown }).detail;
      if (typeof responseDetail === "string") detail = responseDetail;
    }
  } catch {
    // Fall back to the status-based message when the server did not return JSON.
  }
  return new ApiError(response.status, path, detail);
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${env.apiUrl}${path}`, {
    ...init,
    headers,
  });
  if (response.status === 401) unauthorizedHandler?.();
  if (!response.ok) throw await responseError(response, path);
  return schema.parse(await response.json());
}

export const apiClient = {
  getCurrentUser: () => request("/api/v1/auth/me", currentUserSchema),
  getFactory: () => request("/api/v1/factory", z.unknown()),
  getRobots: (signal?: AbortSignal) => request(
    "/api/v1/robots",
    z.array(robotSchema),
    { signal },
  ),
  getRobot: (id: string) => request(`/api/v1/robots/${encodeURIComponent(id)}`, robotSchema),
  getTasks: (signal?: AbortSignal) => request(
    "/api/v1/tasks",
    z.array(taskSchema),
    { signal },
  ),
  getTask: (id: string) => request(`/api/v1/tasks/${encodeURIComponent(id)}`, taskSchema),
  getMetrics: (signal?: AbortSignal) => request(
    "/api/v1/metrics",
    factoryMetricsSchema,
    { signal },
  ),
  getAlerts: (signal?: AbortSignal) => request(
    "/api/v1/alerts",
    z.array(factoryAlertSchema),
    { signal },
  ),
  updateMockConfig: (config: MockFactoryConfig) =>
    request("/api/v1/mock/config", mockFactoryConfigSchema, {
      method: "POST",
      body: JSON.stringify(config),
    }),
  resetMockFactory: () => request("/api/v1/mock/reset", z.unknown(), { method: "POST" }),
  getBaselineScenario: () => request("/api/v1/scenarios/baseline", scenarioSchema),
  getScenarios: () => request("/api/v1/scenarios", z.array(scenarioSchema)),
  getScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}`, scenarioSchema),
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
  getAdminUsers: () => request("/api/v1/admin/users", z.array(adminUserSchema)),
  updateAdminUser: (id: string, update: AdminUserUpdate) =>
    request(`/api/v1/admin/users/${encodeURIComponent(id)}`, adminUserSchema, {
      method: "PATCH",
      body: JSON.stringify(adminUserUpdateSchema.parse(update)),
    }),
  inviteAdminUser: (invite: AdminInviteRequest) =>
    request("/api/v1/admin/users/invite", adminUserSchema, {
      method: "POST",
      body: JSON.stringify(adminInviteRequestSchema.parse(invite)),
    }),
  getAdminAudit: (limit = 100) => request(
    `/api/v1/admin/audit?limit=${Math.min(Math.max(Math.trunc(limit), 1), 100)}`,
    z.array(auditEventSchema),
  ),
};
