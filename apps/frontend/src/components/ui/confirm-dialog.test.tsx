import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./confirm-dialog";

function renderDialog(overrides: Partial<Parameters<typeof ConfirmDialog>[0]> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  const props = {
    title: "Archive layout?",
    message: <p>This action changes the saved layout.</p>,
    confirmLabel: "Archive",
    onConfirm,
    onCancel,
    open: true,
    ...overrides,
  };
  return { ...render(<ConfirmDialog {...props}/>), onConfirm, onCancel, props };
}

describe("ConfirmDialog", () => {
  it("renders an accessible modal and invokes both actions", () => {
    const { onConfirm, onCancel } = renderDialog({ variant: "danger" });
    const dialog = screen.getByRole("dialog", { name: "Archive layout?" });

    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleDescription("This action changes the saved layout.");
    expect(dialog).toHaveClass("danger");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Archive" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("dismisses with Escape or an overlay click but not a panel click", () => {
    const { container, onCancel } = renderDialog();
    const overlay = container.querySelector(".confirm-overlay")!;

    fireEvent.mouseDown(screen.getByRole("dialog"));
    expect(onCancel).not.toHaveBeenCalled();
    fireEvent.mouseDown(overlay);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  it("traps focus and restores the opener when closed", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const { rerender, props } = renderDialog();
    const cancel = screen.getByRole("button", { name: "Cancel" });
    const confirm = screen.getByRole("button", { name: "Archive" });

    cancel.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(confirm).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(cancel).toHaveFocus();

    rerender(<ConfirmDialog {...props} open={false}/>);
    expect(opener).toHaveFocus();
    opener.remove();
  });
});
