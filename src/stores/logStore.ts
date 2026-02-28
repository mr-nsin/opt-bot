import { create } from "zustand";
import type { LogEntry } from "@/lib/types";

const LOG_CAP = 100;

interface LogState {
  logs: LogEntry[];
  filterLevel: string | null;
  filterCategory: string | null;
  autoScroll: boolean;

  addLog: (entry: LogEntry) => void;
  addLogsBatch: (entries: LogEntry[]) => void;
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
      const prev = state.logs[state.logs.length - 1];
      if (
        prev &&
        prev.timestamp === entry.timestamp &&
        prev.message === entry.message &&
        prev.category === entry.category
      ) {
        return state;
      }
      return { logs: [...state.logs, entry].slice(-LOG_CAP) };
    }),
  addLogsBatch: (entries) =>
    set((state) => {
      if (entries.length === 0) return state;
      const combined = [...state.logs, ...entries];
      const deduped: LogEntry[] = [];
      for (const e of combined) {
        const last = deduped[deduped.length - 1];
        if (
          last &&
          last.timestamp === e.timestamp &&
          last.message === e.message &&
          last.category === e.category
        ) continue;
        deduped.push(e);
      }
      return { logs: deduped.slice(-LOG_CAP) };
    }),
  setLogs: (logs) => set({ logs: logs.slice(-LOG_CAP) }),
  clearLogs: () => set({ logs: [] }),
  setFilterLevel: (level) => set({ filterLevel: level }),
  setFilterCategory: (category) => set({ filterCategory: category }),
  setAutoScroll: (auto) => set({ autoScroll: auto }),
}));
