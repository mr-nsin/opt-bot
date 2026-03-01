import { create } from "zustand";

const TOAST_DEDUPE_MS = 2500;

export interface Toast {
  id: string;
  title: string;
  message: string;
  type: "success" | "error" | "warning" | "info";
  timestamp: number;
}

interface NotificationState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id" | "timestamp">) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

let toastCounter = 0;
let lastAdded: { title: string; message: string; timestamp: number } | null = null;

export const useNotificationStore = create<NotificationState>((set, get) => ({
  toasts: [],

  addToast: (toast) => {
    const now = Date.now();
    if (
      lastAdded &&
      lastAdded.title === toast.title &&
      lastAdded.message === toast.message &&
      now - lastAdded.timestamp < TOAST_DEDUPE_MS
    ) {
      return;
    }
    const inState = get().toasts.some(
      (t) =>
        t.title === toast.title &&
        t.message === toast.message &&
        now - t.timestamp < TOAST_DEDUPE_MS
    );
    if (inState) return;
    lastAdded = { title: toast.title, message: toast.message, timestamp: now };

    const id = `toast-${++toastCounter}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id, timestamp: now }].slice(-5),
    }));
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 5000);
  },

  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),

  clearAll: () => set({ toasts: [] }),
}));
