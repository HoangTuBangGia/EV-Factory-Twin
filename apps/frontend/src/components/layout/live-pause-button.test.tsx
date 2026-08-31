import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useFactoryStore } from "@/stores/factory-store";
import { LivePauseButton } from "./live-pause-button";

describe("LivePauseButton", () => {
  beforeEach(() => useFactoryStore.getState().reset());

  it("toggles the global pause indicator", () => {
    render(<LivePauseButton/>);
    const pause = screen.getByRole("button", { name: "Pause live updates" });
    expect(pause).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(pause);
    const resume = screen.getByRole("button", { name: "Resume live updates" });
    expect(resume).toHaveTextContent("PAUSED");
    expect(resume).toHaveAttribute("aria-pressed", "true");
  });

  it("uses an icon-only cockpit presentation", () => {
    render(<LivePauseButton cockpit/>);
    expect(screen.getByRole("button", { name: "Pause live updates" })).toHaveTextContent("");
  });
});
