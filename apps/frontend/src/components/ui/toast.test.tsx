import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toastError, toastInfo, toastSuccess, useToastStore } from "@/stores/toast-store";
import { ToastContainer } from "./toast";

describe("ToastContainer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToastStore.setState({ toasts: [] });
  });

  afterEach(() => vi.useRealTimers());

  it("announces success and dismisses it automatically", () => {
    render(<ToastContainer/>);
    act(() => toastSuccess("Layout saved"));

    expect(screen.getByRole("status")).toHaveTextContent("Layout saved");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");

    act(() => vi.advanceTimersByTime(4000));
    expect(screen.queryByText("Layout saved")).not.toBeInTheDocument();
  });

  it("keeps errors until they are dismissed manually", () => {
    render(<ToastContainer/>);
    act(() => toastError("Save failed"));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Save failed");
    expect(alert).toHaveAttribute("aria-live", "assertive");

    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps only the three newest notifications", () => {
    render(<ToastContainer/>);
    act(() => {
      toastInfo("First");
      toastInfo("Second");
      toastInfo("Third");
      toastInfo("Fourth");
    });

    expect(screen.queryByText("First")).not.toBeInTheDocument();
    expect(screen.getAllByRole("status")).toHaveLength(3);
    expect(screen.getByText("Fourth")).toBeInTheDocument();
  });
});
