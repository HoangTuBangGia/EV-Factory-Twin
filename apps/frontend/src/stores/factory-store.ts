import { create } from "zustand";
import type { FactoryAlert } from "@/schemas/alert";
import type { Command } from "@/schemas/command";
import type { FactoryMetrics } from "@/schemas/metric";
import type { Robot, RobotTelemetry } from "@/schemas/robot";
import type { Scenario } from "@/schemas/scenario";
import type { Task } from "@/schemas/task";

export type ConnectionStatus = "CONNECTING" | "LIVE" | "OFFLINE" | "MOCK";

export interface MetricsSample extends FactoryMetrics {
  timestamp: number;
}

export const METRICS_HISTORY_SAMPLE_INTERVAL_MS = 5_000;
export const METRICS_HISTORY_WINDOW_MS = 5 * 60_000;
const METRICS_HISTORY_LIMIT = Math.ceil(
  METRICS_HISTORY_WINDOW_MS / METRICS_HISTORY_SAMPLE_INTERVAL_MS,
);

function latestCommand(current: Command | undefined, incoming: Command) {
  return current && Date.parse(current.updated_at) > Date.parse(incoming.updated_at)
    ? current
    : incoming;
}

interface FactoryStore {
  robots: Record<string, Robot>;
  tasks: Record<string, Task>;
  metrics: FactoryMetrics | null;
  metricsHistory: MetricsSample[];
  alerts: FactoryAlert[];
  acknowledgedAlertIds: string[];
  commands: Record<string, Command>;
  scenarios: Scenario[];
  factoryRevision: number;
  lastUpdateAt: number | null;
  selectedRobotId: string | null;
  connectionStatus: ConnectionStatus;
  paused: boolean;
  setRobots: (robots: Robot[]) => void;
  updateRobotTelemetry: (telemetry: RobotTelemetry) => void;
  setTasks: (tasks: Task[]) => void;
  updateTask: (task: Task) => void;
  setMetrics: (metrics: FactoryMetrics) => void;
  clearMetricsHistory: () => void;
  setAlerts: (alerts: FactoryAlert[]) => void;
  addAlert: (alert: FactoryAlert) => void;
  acknowledgeAlert: (id: string) => void;
  setCommands: (commands: Command[]) => void;
  updateCommand: (command: Command) => void;
  setScenarios: (scenarios: Scenario[]) => void;
  updateScenario: (scenario: Scenario) => void;
  bumpFactoryRevision: () => void;
  markDataUpdated: (at?: number) => void;
  selectRobot: (id: string | null) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setPaused: (paused: boolean) => void;
  togglePaused: () => void;
  reset: () => void;
}

export const useFactoryStore = create<FactoryStore>((set) => ({
  robots: {}, tasks: {}, metrics: null, metricsHistory: [], alerts: [], acknowledgedAlertIds: [], commands: {}, scenarios: [], factoryRevision: 0, lastUpdateAt: null, selectedRobotId: null,
  connectionStatus: "CONNECTING", paused: false,
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
  setMetrics: (metrics) => set((state) => {
    const timestamp = Date.now();
    const latestSample = state.metricsHistory.at(-1);

    // KPI cards remain realtime, but the chart only receives a new array when
    // its wall-clock sampling interval has elapsed. This prevents telemetry
    // bursts (for example at high simulation speed) from re-rendering ECharts.
    if (
      latestSample
      && timestamp - latestSample.timestamp < METRICS_HISTORY_SAMPLE_INTERVAL_MS
    ) {
      return { metrics };
    }

    const windowStart = timestamp - METRICS_HISTORY_WINDOW_MS;
    const metricsHistory = [
      ...state.metricsHistory.filter((sample) => sample.timestamp >= windowStart),
      { ...metrics, timestamp },
    ].slice(-METRICS_HISTORY_LIMIT);

    return { metrics, metricsHistory };
  }),
  clearMetricsHistory: () => set({ metricsHistory: [] }),
  setAlerts: (alerts) => set((state) => ({
    alerts,
    acknowledgedAlertIds: state.acknowledgedAlertIds.filter((id) => (
      alerts.some((alert) => alert.id === id && alert.status === "ACTIVE")
    )),
  })),
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts.filter((current) => current.dedupe_key !== alert.dedupe_key)]
      .slice(0, 50),
    acknowledgedAlertIds: alert.status === "CLEARED"
      ? state.acknowledgedAlertIds.filter((id) => id !== alert.id)
      : state.acknowledgedAlertIds,
  })),
  acknowledgeAlert: (id) => set((state) => state.acknowledgedAlertIds.includes(id)
    ? state
    : { acknowledgedAlertIds: [...state.acknowledgedAlertIds, id] }),
  setCommands: (commands) => set((state) => ({
    commands: {
      ...state.commands,
      ...Object.fromEntries(commands.map((command) => [
        command.operation_id,
        latestCommand(state.commands[command.operation_id], command),
      ])),
    },
  })),
  updateCommand: (command) => set((state) => ({
    commands: {
      ...state.commands,
      [command.operation_id]: latestCommand(state.commands[command.operation_id], command),
    },
  })),
  setScenarios: (scenarios) => set({ scenarios }),
  updateScenario: (scenario) => set((state) => ({
    scenarios: state.scenarios.some((current) => current.id === scenario.id)
      ? state.scenarios.map((current) => (current.id === scenario.id ? scenario : current))
      : [scenario, ...state.scenarios],
  })),
  bumpFactoryRevision: () => set((state) => ({ factoryRevision: state.factoryRevision + 1 })),
  markDataUpdated: (lastUpdateAt = Date.now()) => set({ lastUpdateAt }),
  selectRobot: (selectedRobotId) => set({ selectedRobotId }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setPaused: (paused) => set({ paused }),
  togglePaused: () => set((state) => ({ paused: !state.paused })),
  reset: () => set({
    robots: {},
    tasks: {},
    metrics: null,
    metricsHistory: [],
    alerts: [],
    acknowledgedAlertIds: [],
    commands: {},
    scenarios: [],
    factoryRevision: 0,
    lastUpdateAt: null,
    selectedRobotId: null,
    connectionStatus: "OFFLINE",
    paused: false,
  }),
}));
