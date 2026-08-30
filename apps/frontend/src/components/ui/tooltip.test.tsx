import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Tooltip } from "./tooltip";

describe("Tooltip", () => {
  it("links its accessible trigger to the tooltip content", () => {
    render(<Tooltip label="Explain throughput" content="Completed tasks per hour"/>);
    const trigger = screen.getByRole("button", { name: "Explain throughput" });
    const tooltip = screen.getByRole("tooltip");

    expect(trigger).toHaveAttribute("aria-describedby", tooltip.id);
    expect(tooltip).toHaveTextContent("Completed tasks per hour");
  });

  it("toggles pinned visibility for touch interaction", () => {
    render(<Tooltip label="Explain throughput" content="Completed tasks per hour"/>);
    const trigger = screen.getByRole("button", { name: "Explain throughput" });

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(trigger.closest(".tooltip")).toHaveClass("open");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger.closest(".tooltip")).not.toHaveClass("open");
  });

  it("dismisses a pinned tooltip with Escape", () => {
    render(<Tooltip label="Explain throughput" content="Completed tasks per hour"/>);
    const trigger = screen.getByRole("button", { name: "Explain throughput" });

    fireEvent.click(trigger);
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).not.toHaveFocus();
  });
});
