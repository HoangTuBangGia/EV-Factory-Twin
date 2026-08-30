import { create } from "zustand";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (type: ToastType, message: string) => void;
  removeToast: (id: string) => void;
}

let counter = 0;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (type, message) => set((state) => {
    const id = `t-${++counter}`;
    const toasts = [...state.toasts, { id, type, message }].slice(-3);
    return { toasts };
  }),
  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id),
  })),
}));

const AUTO_DISMISS_MS: Record<ToastType, number> = {
  success: 4000,
  info: 4000,
  error: 0,
};

export function toastSuccess(message: string) {
  useToastStore.getState().addToast("success", message);
}

export function toastError(message: string) {
  useToastStore.getState().addToast("error", message);
}

export function toastInfo(message: string) {
  useToastStore.getState().addToast("info", message);
}

export function getAutoDismissMs(type: ToastType): number {
  return AUTO_DISMISS_MS[type];
}
