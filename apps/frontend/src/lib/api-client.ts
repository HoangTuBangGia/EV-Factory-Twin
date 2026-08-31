import { z } from "zod";
import { env } from "./env";
import { factoryAlertSchema } from "@/schemas/alert";
import { currentUserSchema, loginResponseSchema } from "@/schemas/auth";
import {
  applyScenarioRequestSchema,
  commandSchema,
  type ApplyScenarioRequest,
} from "@/schemas/command";
import { factoryMetricsSchema } from "@/schemas/metric";
import { mockFactoryConfigSchema, type MockFactoryConfig } from "@/schemas/factory";
import { robotSchema } from "@/schemas/robot";
import {
  createLayoutRequestSchema,
  createLayoutVersionRequestSchema,
  layoutSummarySchema,
  layoutVersionSchema,
  type CreateLayoutRequest,
  type CreateLayoutVersionRequest,
} from "@/schemas/layout";
import {
  optimizationRequestSchema,
  optimizationResultSchema,
  type OptimizationRequest,
} from "@/schemas/optimization";
import {
  scenarioRevisionRequestSchema,
  scenarioRunRequestSchema,
  scenarioSchema,
  type ScenarioRevisionRequest,
  type ScenarioRunRequest,
} from "@/schemas/scenario";
import {
  createTransportTaskRequestSchema,
  taskSchema,
  type CreateTransportTaskRequest,
} from "@/schemas/task";

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

async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
  handleUnauthorized = true,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${env.apiUrl}${path}`, {
    ...init,
    headers,
  });
  if (handleUnauthorized && response.status === 401) unauthorizedHandler?.();
  if (!response.ok) throw await responseError(response, path);
  return schema.parse(await response.json());
}

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${env.apiUrl}${path}`, { ...init, headers });
  if (response.status === 401) unauthorizedHandler?.();
  if (!response.ok) throw await responseError(response, path);
}

export const apiClient = {
  login: (email: string, password: string) => request(
    "/api/v1/auth/login",
    loginResponseSchema,
    { method: "POST", body: JSON.stringify({ email, password }) },
    false,
  ),
  logout: () => requestVoid("/api/v1/auth/logout", { method: "POST" }),
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
  createTransportTask: (input: CreateTransportTaskRequest) => request(
    "/api/v1/tasks",
    commandSchema,
    {
      method: "POST",
      body: JSON.stringify(createTransportTaskRequestSchema.parse(input)),
    },
  ),
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
  getLayouts: () => request("/api/v1/layouts", z.array(layoutSummarySchema)),
  createLayout: (input: CreateLayoutRequest) => request(
    "/api/v1/layouts",
    layoutVersionSchema,
    { method: "POST", body: JSON.stringify(createLayoutRequestSchema.parse(input)) },
  ),
  getLayout: (id: string) => request(
    `/api/v1/layouts/${encodeURIComponent(id)}`,
    layoutVersionSchema,
  ),
  renameLayout: (id: string, name: string) => request(
    `/api/v1/layouts/${encodeURIComponent(id)}`,
    layoutVersionSchema,
    { method: "PATCH", body: JSON.stringify({ name }) },
  ),
  archiveLayout: (id: string) => requestVoid(
    `/api/v1/layouts/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  ),
  createLayoutVersion: (id: string, input: CreateLayoutVersionRequest) => request(
    `/api/v1/layouts/${encodeURIComponent(id)}/versions`,
    layoutVersionSchema,
    { method: "POST", body: JSON.stringify(createLayoutVersionRequestSchema.parse(input)) },
  ),
  getLayoutVersion: (id: string, version: number) => request(
    `/api/v1/layouts/${encodeURIComponent(id)}/versions/${version}`,
    layoutVersionSchema,
  ),
  getBaselineScenario: () => request("/api/v1/scenarios/baseline", scenarioSchema),
  getScenarios: () => request("/api/v1/scenarios", z.array(scenarioSchema)),
  getScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}`, scenarioSchema),
  runScenario: (input: ScenarioRunRequest) =>
    request("/api/v1/scenarios/run", scenarioSchema, {
      method: "POST",
      body: JSON.stringify(scenarioRunRequestSchema.parse(input)),
    }),
  submitScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/submit`, scenarioSchema, {
      method: "POST",
    }),
  approveScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/approve`, scenarioSchema, {
      method: "POST",
    }),
  rejectScenario: (id: string) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/reject`, scenarioSchema, {
      method: "POST",
    }),
  requestScenarioRevision: (id: string, input: ScenarioRevisionRequest) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/request-revision`, scenarioSchema, {
      method: "POST",
      body: JSON.stringify(scenarioRevisionRequestSchema.parse(input)),
    }),
  applyScenario: (id: string, input: ApplyScenarioRequest = {}) =>
    request(`/api/v1/scenarios/${encodeURIComponent(id)}/apply`, commandSchema, {
      method: "POST",
      body: JSON.stringify(applyScenarioRequestSchema.parse(input)),
    }),
  runOptimization: (input: OptimizationRequest) => request(
    "/api/v1/optimizations/run",
    optimizationResultSchema,
    { method: "POST", body: JSON.stringify(optimizationRequestSchema.parse(input)) },
  ),
  getCommands: () => request("/api/v1/commands", z.array(commandSchema)),
  getCommand: (operationId: string) => request(
    `/api/v1/commands/${encodeURIComponent(operationId)}`,
    commandSchema,
  ),
  retryCommand: (operationId: string) => request(
    `/api/v1/commands/${encodeURIComponent(operationId)}/retry`,
    commandSchema,
    { method: "POST" },
  ),
};
