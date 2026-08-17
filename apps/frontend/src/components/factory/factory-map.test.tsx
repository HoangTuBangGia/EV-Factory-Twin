import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { fixtureRobots } from "@/lib/fixtures";
import { FactoryMap } from "./factory-map";

/**
 * jsdom has no WebGL, so FactoryMap falls back to the 2D renderer here. That is
 * the branch that must still satisfy the e2e contract in e2e/hosted-rbac.spec.ts:
 * exactly one .robot-marker element per robot on the page.
 */
vi.mock("@/stores/factory-store", () => ({
  useFactoryStore: (select: (state: unknown) => unknown) => select({
    robots: Object.fromEntries(fixtureRobots.map((robot) => [robot.id, robot])),
    selectedRobotId: "AMR-02",
    selectRobot: () => undefined,
    metrics: { queued_tasks: 3 },
  }),
}));

// jsdom's getContext is unimplemented and logs a stack trace per call rather
// than returning null, so stub the probe's answer instead of reading the noise.
beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

describe("FactoryMap without WebGL", () => {
  it("renders one marker per robot and marks the selection", () => {
    const { container } = render(<FactoryMap/>);

    expect(container.querySelector(".factory-map")).toHaveAttribute("data-view", "2d");
    expect(container.querySelectorAll(".robot-marker")).toHaveLength(fixtureRobots.length);
    expect(container.querySelectorAll(".robot-marker.selected")).toHaveLength(1);
    // AMR-05 sits at 16% battery.
    expect(container.querySelectorAll(".robot-marker.low")).toHaveLength(1);
  });

  it("labels each marker for assistive technology", () => {
    render(<FactoryMap/>);
    expect(screen.getByLabelText("AMR-01, DELIVERING, battery 82 percent")).toBeInTheDocument();
    expect(screen.getByLabelText("AMR-05, CHARGING, battery 16 percent")).toBeInTheDocument();
  });
});
