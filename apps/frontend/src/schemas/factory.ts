import { z } from "zod";

const worldPointSchema = z.object({
  x: z.number().finite(),
  y: z.number().finite(),
});

export const stationTypeSchema = z.enum([
  "BATTERY_BUFFER",
  "MARRIAGE_STATION",
  "CHARGING_STATION",
]);

export const factoryStationSchema = worldPointSchema.extend({
  id: z.string().trim().min(1),
  type: stationTypeSchema,
});

export const factoryRouteSchema = z.object({
  id: z.string().trim().min(1),
  waypoints: z.array(worldPointSchema).min(2),
});

export const noGoZoneSchema = z.object({
  id: z.string().trim().min(1),
  points: z.array(worldPointSchema).min(3),
});

export const factoryLayoutSchema = z.object({
  id: z.string().trim().min(1),
  name: z.string().trim().min(1),
  version: z.number().int().positive(),
  width: z.number().positive().finite(),
  height: z.number().positive().finite(),
  stations: z.array(factoryStationSchema),
  routes: z.array(factoryRouteSchema),
  no_go_zones: z.array(noGoZoneSchema),
}).superRefine((layout, context) => {
  const points = [
    ...layout.stations,
    ...layout.routes.flatMap((route) => route.waypoints),
    ...layout.no_go_zones.flatMap((zone) => zone.points),
  ];
  for (const point of points) {
    if (point.x < 0 || point.x > layout.width || point.y < 0 || point.y > layout.height) {
      context.addIssue({
        code: "custom",
        message: `Layout point (${point.x}, ${point.y}) is outside the factory footprint`,
      });
    }
  }
});

export type WorldPoint = z.infer<typeof worldPointSchema>;
export type FactoryStation = z.infer<typeof factoryStationSchema>;
export type FactoryRoute = z.infer<typeof factoryRouteSchema>;
export type NoGoZone = z.infer<typeof noGoZoneSchema>;
export type FactoryLayout = z.infer<typeof factoryLayoutSchema>;

export const mockFactoryConfigSchema = z.object({
  robot_count: z.number().int().min(1).max(10),
  task_interval_seconds: z.number().min(1).max(60),
  robot_speed_mps: z.number().min(0.1).max(3),
  simulation_speed: z.number().min(0.25).max(10),
  low_battery_threshold: z.number().min(0).max(100),
});

export type MockFactoryConfig = z.infer<typeof mockFactoryConfigSchema>;
