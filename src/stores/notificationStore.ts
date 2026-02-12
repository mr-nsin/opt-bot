import { create } from "zustand";

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

export const useNotificationStore = create<NotificationState>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${++toastCounter}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id, timestamp: Date.now() }].slice(
        -5
      ),
    }));
    // Auto-remove after 5 seconds
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
