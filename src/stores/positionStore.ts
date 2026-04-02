import { create } from "zustand";
import type { Position } from "@/lib/types";

const nr = (r?: string) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);
const normExp = (e?: string) => (e || "").replace(/-/g, "").replace(/\s/g, "").trim();

export function positionKey(symbol: string, strike?: number, right?: string, expiry?: string): string {
  return `${symbol}-${Number(strike ?? 0)}-${nr(right)}-${normExp(expiry)}`;
}

/** Deduplicate positions by (symbol, strike, right, expiry). Keep first occurrence. */
function dedupePositions(positions: Position[]): Position[] {
  const seen = new Set<string>();
  return positions.filter((p) => {
    const key = positionKey(p.symbol, p.strike, p.right, p.expiry);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

const RECENTLY_CLOSED_TTL_MS = 10_000; // 10 seconds

interface PositionState {
  positions: Position[];
  closedPositions: Position[];
  loading: boolean;
  /** Keys of positions currently being closed (close request in-flight) */
  closingPositions: Set<string>;
  /** Keys of recently closed positions — position_update ignores these to prevent ghost re-adds */
  recentlyClosed: Set<string>;

  setPositions: (positions: Position[]) => void;
  updatePosition: (symbol: string, updates: Partial<Position>) => void;
  removePosition: (symbol: string, strike?: number, right?: string, expiry?: string) => void;
  addClosedPosition: (position: Position) => void;
  setLoading: (loading: boolean) => void;
  clearAll: () => void;
  setClosing: (key: string, closing: boolean) => void;
  isRecentlyClosed: (key: string) => boolean;
}

export const usePositionStore = create<PositionState>((set, get) => ({
  positions: [],
  closedPositions: [],
  loading: false,
  closingPositions: new Set(),
  recentlyClosed: new Set(),

  setPositions: (positions) => set({ positions: dedupePositions(positions) }),
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
  removePosition: (symbol, strike, right, expiry) => {
    const key = positionKey(symbol, strike, right, expiry);
    // Add to recently-closed guard to prevent position_update from re-adding
    const rc = new Set(get().recentlyClosed);
    rc.add(key);
    setTimeout(() => {
      const current = get().recentlyClosed;
      if (current.has(key)) {
        const next = new Set(current);
        next.delete(key);
        set({ recentlyClosed: next });
      }
    }, RECENTLY_CLOSED_TTL_MS);

    set((state) => {
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      // Also clear from closingPositions
      const cp = new Set(state.closingPositions);
      cp.delete(key);
      return {
        positions: state.positions.filter((p) => {
          if (p.symbol !== symbol) return true;
          if (strike != null && Number(p.strike) !== strike) return true;
          if (right != null && right !== "" && nr(p.right) !== nr(right)) return true;
          if (expiry != null && expiry !== "" && normExp(p.expiry) !== normExp(expiry)) return true;
          return false;
        }),
        recentlyClosed: rc,
        closingPositions: cp,
      };
    });
  },
  addClosedPosition: (position) =>
    set((state) => ({
      closedPositions: [position, ...state.closedPositions].slice(0, 200),
    })),
  setLoading: (loading) => set({ loading }),
  clearAll: () => set({ positions: [], closedPositions: [], closingPositions: new Set(), recentlyClosed: new Set() }),
  setClosing: (key, closing) =>
    set((state) => {
      const next = new Set(state.closingPositions);
      if (closing) next.add(key); else next.delete(key);
      return { closingPositions: next };
    }),
  isRecentlyClosed: (key) => get().recentlyClosed.has(key),
}));
