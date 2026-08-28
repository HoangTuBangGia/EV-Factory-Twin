import { describe, expect, it } from "vitest";
import {
  applyProgress,
  candidateForLayoutVersion,
  filterQueue,
  isQueueKey,
  latestCommandForScenario,
  nextAction,
  stageState,
} from "./workflow";
import { fixtureApplyCommand, fixtureScenario, fixtureScenarioConfig } from "./fixtures";
import type { Command } from "@/schemas/command";
import type { Scenario, ScenarioStatus } from "@/schemas/scenario";

const DESIGNER_ID = fixtureScenario.created_by ?? "";
const OTHER_ID = "22222222-2222-4222-8222-222222222222";

function scenario(overrides: Partial<Scenario> = {}): Scenario {
  return { ...fixtureScenario, ...overrides };
}

function candidate(id: string, status: ScenarioStatus, createdAt: string, owner = DESIGNER_ID) {
  return scenario({ id, name: id, status, created_at: createdAt, created_by: owner });
}

function command(status: Command["status"], acknowledged = false): Command {
  return {
    ...fixtureApplyCommand,
    status,
    attempts: [{
      ...fixtureApplyCommand.attempts[0],
      status,
      acknowledged_at: acknowledged ? "2026-08-14T00:10:05.000Z" : null,
    }],
  };
}

describe("stageState", () => {
  it("marks passed stages done and the live stage current", () => {
    expect(stageState("APPROVED", "SIMULATED")).toBe("done");
    expect(stageState("APPROVED", "SUBMITTED")).toBe("done");
    expect(stageState("APPROVED", "APPROVED")).toBe("current");
    expect(stageState("APPROVED", "APPLIED")).toBe("pending");
  });

  it("closes every stage once the candidate is applied", () => {
    expect(stageState("APPLIED", "APPLIED")).toBe("done");
  });

  it("marks review as rejected instead of current for the terminal status", () => {
    expect(stageState("REJECTED", "SIMULATED")).toBe("done");
    expect(stageState("REJECTED", "SUBMITTED")).toBe("rejected");
    expect(stageState("REJECTED", "APPROVED")).toBe("pending");
  });

  it("leaves every stage pending for a draft that was never simulated", () => {
    expect(stageState("DRAFT", "SIMULATED")).toBe("pending");
  });
});

describe("applyProgress", () => {
  it("returns null when no command was ever queued", () => {
    expect(applyProgress(null)).toBeNull();
  });

  it("advances through queued, acknowledged, and applied", () => {
    expect(applyProgress(command("PENDING"))).toEqual({ index: 0, failed: false });
    expect(applyProgress(command("ACKNOWLEDGED", true))).toEqual({ index: 1, failed: false });
    expect(applyProgress(command("COMPLETED", true))).toEqual({ index: 2, failed: false });
  });

  it("keeps the reached phase when the bridge failed after acknowledging", () => {
    expect(applyProgress(command("FAILED", true))).toEqual({ index: 1, failed: true });
    expect(applyProgress(command("TIMED_OUT"))).toEqual({ index: 0, failed: true });
  });
});

describe("filterQueue", () => {
  const scenarios = [
    candidate("a", "SUBMITTED", "2026-08-14T00:00:00.000Z"),
    candidate("b", "APPROVED", "2026-08-14T01:00:00.000Z", OTHER_ID),
    candidate("c", "APPLIED", "2026-08-14T02:00:00.000Z", OTHER_ID),
    candidate("d", "SIMULATED", "2026-08-14T03:00:00.000Z"),
  ];

  it("keeps every candidate for the default queue", () => {
    expect(filterQueue(scenarios, "all", DESIGNER_ID)).toHaveLength(4);
  });

  it("selects candidates by workflow status", () => {
    expect(filterQueue(scenarios, "awaiting").map((item) => item.id)).toEqual(["a"]);
    expect(filterQueue(scenarios, "approved").map((item) => item.id)).toEqual(["b"]);
    expect(filterQueue(scenarios, "applied").map((item) => item.id)).toEqual(["c"]);
  });

  it("selects the signed-in designer's own candidates", () => {
    expect(filterQueue(scenarios, "mine", DESIGNER_ID).map((item) => item.id)).toEqual(["a", "d"]);
  });
});

describe("candidateForLayoutVersion", () => {
  const scenarios = [
    scenario({ id: "old", created_at: "2026-08-14T00:00:00.000Z" }),
    scenario({ id: "new", created_at: "2026-08-14T05:00:00.000Z" }),
    scenario({
      id: "other-version",
      created_at: "2026-08-14T09:00:00.000Z",
      config: { ...fixtureScenarioConfig, layout_version: 2 },
    }),
  ];

  it("resolves the newest scenario benchmarked on that exact version", () => {
    expect(candidateForLayoutVersion(scenarios, "LAYOUT-DEFAULT", 1)?.id).toBe("new");
    expect(candidateForLayoutVersion(scenarios, "LAYOUT-DEFAULT", 2)?.id).toBe("other-version");
  });

  it("returns null for a version that has never been simulated", () => {
    expect(candidateForLayoutVersion(scenarios, "LAYOUT-DEFAULT", 7)).toBeNull();
    expect(candidateForLayoutVersion(scenarios, "LAYOUT-OTHER", 1)).toBeNull();
  });
});

describe("latestCommandForScenario", () => {
  it("selects the newest durable operation for the candidate", () => {
    const old = {
      ...fixtureApplyCommand,
      operation_id: "11111111-1111-4111-8111-111111111111",
      updated_at: "2026-08-14T00:11:00.000Z",
    };
    const retried = {
      ...fixtureApplyCommand,
      operation_id: "22222222-2222-4222-8222-222222222222",
      updated_at: "2026-08-14T00:12:00.000Z",
    };
    const other = { ...fixtureApplyCommand, scenario_id: "SCN-OTHER" };

    expect(latestCommandForScenario([old, other, retried], fixtureScenario.id)?.operation_id)
      .toBe(retried.operation_id);
    expect(latestCommandForScenario([old], "SCN-MISSING")).toBeNull();
  });
});

describe("nextAction", () => {
  it("sends a designer without candidates to the layout editor", () => {
    const action = nextAction("DESIGNER", [], DESIGNER_ID);
    expect(action.headline).toBe("No simulated candidate yet");
    expect(action.cta?.href).toBe("/layouts");
  });

  it("tells a designer that a simulated candidate still needs submitting", () => {
    const scenarios = [candidate("draft-me", "SIMULATED", "2026-08-14T00:00:00.000Z")];
    expect(nextAction("DESIGNER", scenarios, DESIGNER_ID).headline)
      .toBe("draft-me is simulated but not submitted");
  });

  it("ignores candidates belonging to another designer", () => {
    const scenarios = [candidate("theirs", "SUBMITTED", "2026-08-14T09:00:00.000Z", OTHER_ID)];
    expect(nextAction("DESIGNER", scenarios, DESIGNER_ID).headline)
      .toBe("No simulated candidate yet");
  });

  it("explains that a rejected candidate cannot be resubmitted", () => {
    const scenarios = [candidate("blocked", "REJECTED", "2026-08-14T00:00:00.000Z")];
    const action = nextAction("DESIGNER", scenarios, DESIGNER_ID);
    expect(action.headline).toBe("blocked was rejected");
    expect(action.hint).toContain("cannot be resubmitted");
  });

  it("prioritises the review queue over the apply queue for a monitor", () => {
    const scenarios = [
      candidate("a", "SUBMITTED", "2026-08-14T00:00:00.000Z"),
      candidate("b", "SUBMITTED", "2026-08-14T01:00:00.000Z"),
      candidate("c", "APPROVED", "2026-08-14T02:00:00.000Z"),
    ];
    const action = nextAction("MONITOR", scenarios, OTHER_ID);
    expect(action.headline).toBe("2 candidates awaiting your review");
    expect(action.cta?.href).toBe("/scenarios?queue=awaiting");
  });

  it("points a monitor at approved candidates when nothing awaits review", () => {
    const scenarios = [candidate("c", "APPROVED", "2026-08-14T02:00:00.000Z")];
    const action = nextAction("MONITOR", scenarios, OTHER_ID);
    expect(action.headline).toBe("1 approved candidate ready to apply");
    expect(action.cta?.href).toBe("/scenarios?queue=approved");
  });

  it("stays quiet for a monitor with an empty queue", () => {
    expect(nextAction("MONITOR", [], OTHER_ID).headline).toBe("Nothing needs your review");
  });
});

describe("isQueueKey", () => {
  it("accepts known queues and rejects anything else", () => {
    expect(isQueueKey("awaiting")).toBe(true);
    expect(isQueueKey("nope")).toBe(false);
    expect(isQueueKey(null)).toBe(false);
  });
});
