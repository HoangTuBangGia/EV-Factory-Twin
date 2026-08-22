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

export type TaskStatus = z.infer<typeof taskStatusSchema>;
export type Task = z.infer<typeof taskSchema>;
