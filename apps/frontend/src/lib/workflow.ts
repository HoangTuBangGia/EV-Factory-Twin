import type { AppRole } from "@/schemas/auth";
import type { Command } from "@/schemas/command";
import type { Scenario, ScenarioStatus } from "@/schemas/scenario";

/**
 * Review stages a candidate walks through. Mirrors the backend transition
 * table (SIMULATED -> SUBMITTED -> APPROVED -> APPLIED); REJECTED is terminal
 * and therefore rendered as a failed review rather than a fifth stage.
 */
export const WORKFLOW_STAGES = ["SIMULATED", "SUBMITTED", "APPROVED", "APPLIED"] as const;

/** Apply is two phase: the command is queued first, runtime changes later. */
export const APPLY_PHASES = ["Apply queued", "Bridge acknowledged", "Applied"] as const;

export const QUEUE_KEYS = ["all", "awaiting", "mine", "approved", "applied"] as const;

export type WorkflowStage = (typeof WORKFLOW_STAGES)[number];
export type StageState = "done" | "current" | "rejected" | "pending";
export type QueueKey = (typeof QUEUE_KEYS)[number];

export const QUEUE_LABELS: Readonly<Record<QueueKey, string>> = {
  all: "All candidates",
  awaiting: "Awaiting review",
  mine: "My candidates",
  approved: "Ready to apply",
  applied: "Applied",
};

export interface NextAction {
  headline: string;
  hint: string;
  cta: { label: string; href: string } | null;
}

const LAYOUT_EDITOR = { label: "Open layout editor", href: "/layouts" };
const MY_CANDIDATES = { label: "Open my candidates", href: "/scenarios?queue=mine" };

export function isQueueKey(value: string | null | undefined): value is QueueKey {
  return QUEUE_KEYS.includes(value as QueueKey);
}

function reachedStage(status: ScenarioStatus) {
  switch (status) {
    case "DRAFT": return -1;
    case "SIMULATED": return 0;
    case "SUBMITTED":
    case "REJECTED": return 1;
    case "APPROVED": return 2;
    case "APPLIED": return 3;
  }
}

export function stageState(status: ScenarioStatus, stage: WorkflowStage): StageState {
  const reached = reachedStage(status);
  const index = WORKFLOW_STAGES.indexOf(stage);
  if (index > reached) return "pending";
  if (index < reached) return "done";
  if (status === "REJECTED") return "rejected";
  return status === "APPLIED" ? "done" : "current";
}

/**
 * Acknowledgement is read from the attempts rather than the status so a
 * command that later failed still shows how far the bridge got.
 */
export function applyProgress(command: Command | null | undefined) {
  if (!command) return null;
  const acknowledged = command.attempts.some((attempt) => attempt.acknowledged_at !== null);
  return {
    index: command.status === "COMPLETED" ? 2 : acknowledged ? 1 : 0,
    failed: command.status === "FAILED" || command.status === "TIMED_OUT",
  };
}

export function filterQueue(scenarios: Scenario[], queue: QueueKey, userId = "") {
  switch (queue) {
    case "awaiting": return scenarios.filter((scenario) => scenario.status === "SUBMITTED");
    case "approved": return scenarios.filter((scenario) => scenario.status === "APPROVED");
    case "applied": return scenarios.filter((scenario) => scenario.status === "APPLIED");
    case "mine": return scenarios.filter((scenario) => scenario.created_by === userId);
    case "all": return scenarios;
  }
}

/** Newest candidate first; the backend list is not ordered for presentation. */
export function newestFirst(scenarios: Scenario[]) {
  return [...scenarios].sort((left, right) => (
    Date.parse(right.created_at) - Date.parse(left.created_at)
  ));
}

/**
 * A candidate is derived, not stored: a layout version carries no workflow
 * status, so the newest scenario benchmarked on that exact version represents
 * it. Returns null while a version has never been simulated.
 */
export function candidateForLayoutVersion(
  scenarios: Scenario[],
  layoutId: string,
  version: number,
): Scenario | null {
  return newestFirst(scenarios.filter((scenario) => (
    scenario.config.layout_id === layoutId && scenario.config.layout_version === version
  )))[0] ?? null;
}

function designerAction(scenarios: Scenario[], userId: string): NextAction {
  const latest = newestFirst(filterQueue(scenarios, "mine", userId))[0];
  if (!latest || latest.status === "DRAFT") {
    return {
      headline: "No simulated candidate yet",
      hint: "Save a layout revision, then simulate it to produce KPIs a Monitor can review.",
      cta: LAYOUT_EDITOR,
    };
  }
  switch (latest.status) {
    case "SIMULATED": return {
      headline: `${latest.name} is simulated but not submitted`,
      hint: "A Monitor cannot see it until you submit it for review.",
      cta: MY_CANDIDATES,
    };
    case "SUBMITTED": return {
      headline: `${latest.name} is waiting for Monitor review`,
      hint: "You cannot approve or apply your own candidate.",
      cta: MY_CANDIDATES,
    };
    case "APPROVED": return {
      headline: `${latest.name} is approved and waiting to be applied`,
      hint: "A Monitor applies it; the factory runtime changes only then.",
      cta: MY_CANDIDATES,
    };
    case "APPLIED": return {
      headline: `${latest.name} is live in the factory`,
      hint: "Save a new layout revision to propose the next improvement.",
      cta: LAYOUT_EDITOR,
    };
    default: return {
      headline: `${latest.name} was rejected`,
      hint: "A rejected candidate cannot be resubmitted. Adjust the layout and simulate a new one.",
      cta: LAYOUT_EDITOR,
    };
  }
}

function monitorAction(scenarios: Scenario[]): NextAction {
  const awaiting = filterQueue(scenarios, "awaiting").length;
  if (awaiting > 0) {
    return {
      headline: `${awaiting} candidate${awaiting === 1 ? "" : "s"} awaiting your review`,
      hint: "Compare each candidate with the baseline before approving it.",
      cta: { label: "Open review queue", href: "/scenarios?queue=awaiting" },
    };
  }
  const approved = filterQueue(scenarios, "approved").length;
  if (approved > 0) {
    return {
      headline: `${approved} approved candidate${approved === 1 ? "" : "s"} ready to apply`,
      hint: "Applying queues a bridge command; runtime resets when the bridge completes it.",
      cta: { label: "Open apply queue", href: "/scenarios?queue=approved" },
    };
  }
  return {
    headline: "Nothing needs your review",
    hint: "Designers submit candidates here after simulating them.",
    cta: { label: "Open candidates", href: "/scenarios" },
  };
}

export function nextAction(role: AppRole, scenarios: Scenario[], userId: string): NextAction {
  return role === "DESIGNER" ? designerAction(scenarios, userId) : monitorAction(scenarios);
}
