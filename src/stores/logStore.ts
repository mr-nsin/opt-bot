import { create } from "zustand";
import type { LogEntry } from "@/lib/types";

interface LogState {
  logs: LogEntry[];
  filterLevel: string | null;
  filterCategory: string | null;
  autoScroll: boolean;

  addLog: (entry: LogEntry) => void;
  setLogs: (logs: LogEntry[]) => void;
  clearLogs: () => void;
  setFilterLevel: (level: string | null) => void;
  setFilterCategory: (category: string | null) => void;
  setAutoScroll: (auto: boolean) => void;
}

export const useLogStore = create<LogState>((set) => ({
  logs: [],
  filterLevel: null,
  filterCategory: null,
  autoScroll: true,

  addLog: (entry) =>
    set((state) => {
      // Dedupe: avoid duplicate lines (e.g. same event delivered twice or from Rust buffer + event)
      const prev = state.logs[state.logs.length - 1];
      if (
        prev &&
        prev.timestamp === entry.timestamp &&
        prev.message === entry.message &&
        prev.category === entry.category
      ) {
        return state;
      }
      return {
        logs: [...state.logs, entry].slice(-500), // Keep last 500 logs
      };
    }),
  setLogs: (logs) => set({ logs }),
  clearLogs: () => set({ logs: [] }),
  setFilterLevel: (level) => set({ filterLevel: level }),
  setFilterCategory: (category) => set({ filterCategory: category }),
  setAutoScroll: (auto) => set({ autoScroll: auto }),
}));
