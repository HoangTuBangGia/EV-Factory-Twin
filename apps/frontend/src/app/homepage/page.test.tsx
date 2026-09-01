import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Homepage from "./page";

describe("Homepage", () => {
  it("introduces the product and offers a clear sign-in path", () => {
    render(<Homepage/>);

    expect(screen.getByRole("heading", { name: /Quan sát nhà máy/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Truy cập hệ thống/i })).toHaveAttribute("href", "/login");
    expect(screen.getByText("Realtime factory twin")).toBeInTheDocument();
    expect(screen.getByText("Human approval")).toBeInTheDocument();
  });
});
