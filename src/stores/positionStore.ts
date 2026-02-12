import { create } from "zustand";
import type { Position } from "@/lib/types";

interface PositionState {
  positions: Position[];
  closedPositions: Position[];
  loading: boolean;

  setPositions: (positions: Position[]) => void;
  updatePosition: (symbol: string, updates: Partial<Position>) => void;
  removePosition: (symbol: string) => void;
  addClosedPosition: (position: Position) => void;
  setLoading: (loading: boolean) => void;
  clearAll: () => void;
}

export const usePositionStore = create<PositionState>((set) => ({
  positions: [],
  closedPositions: [],
  loading: false,

  setPositions: (positions) => set({ positions }),
  updatePosition: (symbol, updates) =>
    set((state) => ({
      positions: state.positions.map((p) =>
        p.symbol === symbol ? { ...p, ...updates } : p
      ),
    })),
  removePosition: (symbol) =>
    set((state) => ({
      positions: state.positions.filter((p) => p.symbol !== symbol),
    })),
  addClosedPosition: (position) =>
    set((state) => ({
      closedPositions: [position, ...state.closedPositions].slice(0, 200),
    })),
  setLoading: (loading) => set({ loading }),
  clearAll: () => set({ positions: [], closedPositions: [] }),
}));
