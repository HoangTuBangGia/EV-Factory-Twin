import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { fixtureRobots } from "@/lib/fixtures";
import { defaultFactoryLayout } from "@/lib/factory-layout";
import { factoryLayoutSchema } from "@/schemas/factory";
import { FactoryMap } from "./factory-map";

const selectRobotSpy = vi.hoisted(() => vi.fn());

/**
 * jsdom has no WebGL, so FactoryMap falls back to the 2D renderer here. That is
 * the branch that must still satisfy the e2e contract in e2e/hosted-rbac.spec.ts:
 * exactly one .robot-marker element per robot on the page.
 */
vi.mock("@/stores/factory-store", () => ({
  useFactoryStore: (select: (state: unknown) => unknown) => select({
    robots: Object.fromEntries(fixtureRobots.map((robot) => [robot.id, robot])),
    selectedRobotId: "AMR-02",
    selectRobot: selectRobotSpy,
    metrics: { queued_tasks: 3 },
  }),
}));

// jsdom's getContext is unimplemented and logs a stack trace per call rather
// than returning null, so stub the probe's answer instead of reading the noise.
beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

describe("FactoryMap without WebGL", () => {
  it("supports forcing the realtime 2D renderer", () => {
    const { container } = render(<FactoryMap view="2d"/>);

    expect(container.querySelector(".factory-map")).toHaveAttribute("data-view", "2d");
    expect(screen.getByRole("img", { name: "2D factory map" })).toBeInTheDocument();
  });

  it("renders the detailed plant blueprint with live robot coordinates", () => {
    const { container } = render(<FactoryMap view="2d" twoDimensionalVariant="plant"/>);

    expect(screen.getByRole("img", { name: "2D EV factory plant map" })).toHaveAttribute(
      "viewBox",
      "-10 -26 140 52",
    );
    expect(container.querySelectorAll(".plant-zone")).toHaveLength(3);
    expect(container.querySelectorAll(".robot-marker")).toHaveLength(fixtureRobots.length);
    expect(container.querySelector('[data-robot-id="AMR-01"]')).toHaveAttribute(
      "transform",
      "translate(11.5 -1.7) rotate(0)",
    );
    expect(container.querySelector(".map-hud")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Zone B" }));
    expect(screen.getByRole("img", { name: "2D EV factory plant map" })).toHaveAttribute(
      "viewBox",
      "36 -24 58 48",
    );

    selectRobotSpy.mockClear();
    fireEvent.click(screen.getByLabelText("AMR-01, DELIVERING, battery 82 percent"));
    expect(selectRobotSpy).toHaveBeenCalledWith("AMR-01");
  });

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

  it("applies layer visibility to the 2D fallback", () => {
    const { container } = render(<FactoryMap layers={{
      stations: false,
      routes: false,
      noGoZones: false,
    }}/>);

    expect(container.querySelector(".fm-lane")).not.toBeInTheDocument();
    expect(container.querySelector(".fm-zone")).not.toBeInTheDocument();
    expect(container.querySelector(".fm-nogo")).not.toBeInTheDocument();
    expect(container.querySelectorAll(".robot-marker")).toHaveLength(fixtureRobots.length);
  });

  it("renders a supplied layout instead of fixed factory geometry", () => {
    const layout = factoryLayoutSchema.parse({
      ...defaultFactoryLayout,
      id: "LAYOUT-WIDE",
      version: 2,
      width: 30,
      height: 20,
      stations: defaultFactoryLayout.stations.map((station) => (
        station.type === "BATTERY_BUFFER" ? { ...station, x: 4, y: 5 } : station
      )),
    });
    const { container } = render(<FactoryMap view="2d" layout={layout}/>);

    expect(screen.getByRole("img", { name: "2D factory map" })).toHaveAttribute(
      "viewBox",
      "0 0 30 20",
    );
    expect(container.querySelector('.fm-zone circle[cx="4"][cy="15"]')).toBeInTheDocument();
    expect(container.querySelector(".map-scale")).toHaveTextContent("30 × 20 m");
  });
});
