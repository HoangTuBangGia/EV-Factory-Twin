import { z } from "zod";

export const taskStatusSchema = z.enum([
  "QUEUED", "ASSIGNED", "PICKUP", "DELIVERING", "COMPLETED", "FAILED", "TIMED_OUT",
  "IN_PROGRESS", "DELIVERED",
]);

export const taskSchema = z.object({
  task_id: z.string(),
  type: z.literal("DELIVER_BATTERY"),
  payload_id: z.string(),
  pickup: z.string(),
  dropoff: z.string(),
  assigned_robot_id: z.string().nullable(),
  status: taskStatusSchema,
  created_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});

export const createTransportTaskRequestSchema = z.object({
  task_id: z.string().min(1).max(100).regex(/^[A-Z][A-Z0-9_-]*$/),
  payload_id: z.string().min(1).max(100).regex(/^[A-Z][A-Z0-9_-]*$/),
  pickup_station_id: z.string().min(1).max(100),
  dropoff_station_id: z.string().min(1).max(100),
  navigation_timeout_seconds: z.number().positive().max(300).default(30),
  max_retries: z.number().int().min(0).max(5).default(1),
}).refine((value) => value.pickup_station_id !== value.dropoff_station_id, {
  message: "Pickup and drop-off stations must differ",
  path: ["dropoff_station_id"],
});

export type TaskStatus = z.infer<typeof taskStatusSchema>;
export type Task = z.infer<typeof taskSchema>;
export type CreateTransportTaskRequest = z.input<typeof createTransportTaskRequestSchema>;
