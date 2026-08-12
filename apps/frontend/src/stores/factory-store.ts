import { create } from "zustand";
import type { FactoryAlert } from "@/schemas/alert";
import type { FactoryMetrics } from "@/schemas/metric";
import type { Robot, RobotTelemetry } from "@/schemas/robot";
import type { Task } from "@/schemas/task";

export type ConnectionStatus = "CONNECTING" | "LIVE" | "OFFLINE" | "MOCK";

interface FactoryStore {
  robots: Record<string, Robot>;
  tasks: Record<string, Task>;
  metrics: FactoryMetrics | null;
  alerts: FactoryAlert[];
  selectedRobotId: string | null;
  connectionStatus: ConnectionStatus;
  setRobots: (robots: Robot[]) => void;
  updateRobotTelemetry: (telemetry: RobotTelemetry) => void;
  setTasks: (tasks: Task[]) => void;
  updateTask: (task: Task) => void;
  setMetrics: (metrics: FactoryMetrics) => void;
  setAlerts: (alerts: FactoryAlert[]) => void;
  addAlert: (alert: FactoryAlert) => void;
  selectRobot: (id: string | null) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const useFactoryStore = create<FactoryStore>((set) => ({
  robots: {}, tasks: {}, metrics: null, alerts: [], selectedRobotId: null,
  connectionStatus: "CONNECTING",
  setRobots: (robots) => set({ robots: Object.fromEntries(robots.map((robot) => [robot.id, robot])) }),
  updateRobotTelemetry: (telemetry) => set((state) => {
    const current = state.robots[telemetry.robot_id];
    if (!current) return state;
    return { robots: { ...state.robots, [telemetry.robot_id]: {
      ...current, status: telemetry.status, battery: telemetry.battery, pose: telemetry.pose,
      velocity: telemetry.velocity, task_id: telemetry.task_id, payload_id: telemetry.payload_id,
      last_seen_at: telemetry.timestamp,
    } } };
  }),
  setTasks: (tasks) => set({ tasks: Object.fromEntries(tasks.map((task) => [task.task_id, task])) }),
  updateTask: (task) => set((state) => ({ tasks: { ...state.tasks, [task.task_id]: task } })),
  setMetrics: (metrics) => set({ metrics }),
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts].slice(0, 50) })),
  selectRobot: (selectedRobotId) => set({ selectedRobotId }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
