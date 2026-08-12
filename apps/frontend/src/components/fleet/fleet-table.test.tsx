import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { fixtureRobots } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";
import { FleetTable } from "./fleet-table";

describe("FleetTable", () => {
  beforeEach(() => useFactoryStore.getState().setRobots(fixtureRobots));
  it("renders robot identity, battery and status", () => {
    render(<FleetTable compact/>);
    expect(screen.getByText("AMR-01")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("DELIVERING")).toBeInTheDocument();
  });
});
