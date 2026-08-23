import { z } from "zod";

const utcDateTimeSchema = z.string().datetime({ offset: true });
const identifierSchema = z.string().min(1).max(80).regex(/^[A-Z][A-Z0-9_-]*$/);

export const pointSchema = z.object({
  x: z.number().finite(),
  y: z.number().finite(),
});

export const layoutStationSchema = pointSchema.extend({
  id: identifierSchema,
  type: z.enum(["BATTERY_BUFFER", "MARRIAGE_STATION", "CHARGING_STATION"]),
});

export const layoutRouteSchema = z.object({
  id: identifierSchema,
  start_station_id: z.string().min(1).max(80),
  end_station_id: z.string().min(1).max(80),
  waypoints: z.array(pointSchema).min(2).max(200),
});

export const polygonZoneSchema = z.object({
  id: identifierSchema,
  points: z.array(pointSchema).min(3).max(100),
});

export const congestionZoneSchema = polygonZoneSchema.extend({
  delay_multiplier: z.number().min(1).max(10),
});

export const layoutRuntimeConfigSchema = z.object({
  robot_count: z.number().int().min(2).max(50),
  demand_interval_seconds: z.number().min(0.1).max(3_600),
  robot_speed_mps: z.number().positive().max(10),
  charger_count: z.number().int().min(1).max(20),
});

export const layoutVersionContentSchema = z.object({
  width: z.number().positive().max(10_000),
  height: z.number().positive().max(10_000),
  stations: z.array(layoutStationSchema).min(3).max(200),
  routes: z.array(layoutRouteSchema).min(1).max(200),
  no_go_zones: z.array(polygonZoneSchema).max(100),
  congestion_zones: z.array(congestionZoneSchema).max(100),
  config: layoutRuntimeConfigSchema,
});

export const layoutVersionSchema = layoutVersionContentSchema.extend({
  layout_id: z.string().min(1),
  name: z.string().min(1),
  version: z.number().int().min(1),
  created_by: z.string().uuid(),
  created_at: utcDateTimeSchema,
  archived_at: utcDateTimeSchema.nullable(),
});

export const layoutSummarySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  latest_version: z.number().int().min(1),
  created_by: z.string().uuid(),
  created_at: utcDateTimeSchema,
  archived_at: utcDateTimeSchema.nullable(),
});

export const createLayoutRequestSchema = z.object({
  name: z.string().trim().min(1).max(120),
  content: layoutVersionContentSchema,
});

export const createLayoutVersionRequestSchema = z.object({
  content: layoutVersionContentSchema,
});

export type LayoutVersionContent = z.infer<typeof layoutVersionContentSchema>;
export type LayoutVersion = z.infer<typeof layoutVersionSchema>;
export type LayoutSummary = z.infer<typeof layoutSummarySchema>;
export type CreateLayoutRequest = z.infer<typeof createLayoutRequestSchema>;
export type CreateLayoutVersionRequest = z.infer<typeof createLayoutVersionRequestSchema>;
