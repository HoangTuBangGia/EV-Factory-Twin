import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Battery } from "./battery";

describe("Battery", () => {
  it("shows its level", () => { render(<Battery value={82}/>); expect(screen.getByText("82%")).toBeInTheDocument(); });
  it("exposes a low-battery warning", () => { render(<Battery value={15}/>); expect(screen.getByLabelText("Low battery")).toBeInTheDocument(); });
});
