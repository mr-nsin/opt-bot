import { create } from "zustand";
import type { Position } from "@/lib/types";

const nr = (r?: string) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);

interface PositionState {
  positions: Position[];
  closedPositions: Position[];
  loading: boolean;

  setPositions: (positions: Position[]) => void;
  updatePosition: (symbol: string, updates: Partial<Position>) => void;
  removePosition: (symbol: string, strike?: number, right?: string, expiry?: string) => void;
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
    set((state) => {
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      return {
        positions: state.positions.map((p) =>
          p.symbol === symbol &&
          (updates.strike == null || Number(p.strike) === Number(updates.strike)) &&
          (updates.right == null || nr(p.right) === nr(updates.right)) &&
          (updates.expiry == null || updates.expiry === "" || normExp(p.expiry) === normExp(updates.expiry))
            ? { ...p, ...updates }
            : p
        ),
      };
    }),
  removePosition: (symbol, strike, right, expiry) =>
    set((state) => {
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      return {
        positions: state.positions.filter((p) => {
          if (p.symbol !== symbol) return true;
          if (strike != null && Number(p.strike) !== strike) return true;
          if (right != null && right !== "" && nr(p.right) !== nr(right)) return true;
          if (expiry != null && expiry !== "" && normExp(p.expiry) !== normExp(expiry)) return true;
          return false;
        }),
      };
    }),
  addClosedPosition: (position) =>
    set((state) => ({
      closedPositions: [position, ...state.closedPositions].slice(0, 200),
    })),
  setLoading: (loading) => set({ loading }),
  clearAll: () => set({ positions: [], closedPositions: [] }),
}));
