import { create } from "zustand";
import type { Position } from "@/lib/types";

/** Normalize option right for matching — align with Rust `norm_right` / `norm_pos_right`. */
export const normRight = (r?: string) => {
  if (!r) return "";
  const u = r.toUpperCase();
  if (u.startsWith("C")) return "C";
  if (u.startsWith("P")) return "P";
  return r;
};

/** Normalize expiry for matching (IBKR may send 20260313 vs 2026-03-13). */
export const normExpiry = (e?: string) => (e || "").replace(/-/g, "").replace(/\s/g, "").trim();

const nr = normRight;
const normExp = normExpiry;

/** Stable key for open-position dedupe / merge (must match useTradingEvents + Rust norm_exp). */
export function positionRowKey(p: {
  symbol?: string;
  strike?: number;
  right?: string;
  expiry?: string;
}): string {
  return `${p.symbol ?? ""}-${Number(p.strike ?? 0)}-${nr(p.right)}-${normExp(p.expiry)}`;
}

/** Deduplicate positions by (symbol, strike, right, expiry). Keep first occurrence. */
function dedupePositions(positions: Position[]): Position[] {
  const seen = new Set<string>();
  return positions.filter((p) => {
    const key = `${p.symbol}-${Number(p.strike ?? 0)}-${nr(p.right)}-${normExp(p.expiry)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

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

  setPositions: (positions) => set({ positions: dedupePositions(positions) }),
  updatePosition: (symbol, updates) =>
    set((state) => ({
      positions: state.positions.map((p) =>
        p.symbol === symbol &&
        (updates.strike == null || Number(p.strike) === Number(updates.strike)) &&
        (updates.right == null || nr(p.right) === nr(updates.right)) &&
        (updates.expiry == null || updates.expiry === "" || normExp(p.expiry) === normExp(updates.expiry))
          ? { ...p, ...updates }
          : p
      ),
    })),
  removePosition: (symbol, strike, right, expiry) =>
    set((state) => ({
      positions: state.positions.filter((p) => {
        if (p.symbol !== symbol) return true;
        if (strike != null && Number(p.strike) !== strike) return true;
        if (right != null && right !== "" && nr(p.right) !== nr(right)) return true;
        if (expiry != null && expiry !== "" && normExp(p.expiry) !== normExp(expiry)) return true;
        return false;
      }),
    })),
  addClosedPosition: (position) =>
    set((state) => ({
      closedPositions: [position, ...state.closedPositions].slice(0, 200),
    })),
  setLoading: (loading) => set({ loading }),
  clearAll: () => set({ positions: [], closedPositions: [] }),
}));
