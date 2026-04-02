import { useCallback, useEffect } from "react";
import { positions as positionsApi } from "@/lib/tauri-commands";
import { usePositionStore } from "@/stores/positionStore";
import { useTauriEvent } from "./useTauri";
import type { Position } from "@/lib/types";

export function usePositions() {
  const { positions, closedPositions, loading, setPositions, updatePosition, removePosition, addClosedPosition, setLoading } =
    usePositionStore();

  // Listen to position updates — use getState() to avoid stale closure
  useTauriEvent<Position>("trading:position_update", (data) => {
    const current = usePositionStore.getState().positions;
    const normalRight = (r: string | undefined) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);
    const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
    const existing = current.find(
      (p) =>
        p.symbol === data.symbol &&
        Number(p.strike) === Number(data.strike) &&
        normalRight(p.right) === normalRight(data.right) &&
        normExp(p.expiry) === normExp(data.expiry)
    );
    if (existing) {
      updatePosition(data.symbol, data);
    } else {
      usePositionStore.getState().setPositions([...current, data]);
    }
  });

  // Move position from active → closed on trade_closed
  useTauriEvent("trading:trade_closed", (data: any) => {
    if (data.symbol) {
      const current = usePositionStore.getState().positions;
      const nr = (r: string | undefined) => r === "CALL" ? "C" : r === "PUT" ? "P" : r;
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      const pos = current.find(
        (p) =>
          p.symbol === data.symbol &&
          (data.strike == null || Number(p.strike) === Number(data.strike)) &&
          (data.right == null || nr(p.right) === nr(data.right)) &&
          (data.expiry == null || data.expiry === "" || normExp(p.expiry) === normExp(data.expiry))
      );
      if (pos) {
        addClosedPosition({ ...pos, ...data });
        removePosition(
          data.symbol,
          data.strike != null ? Number(data.strike) : undefined,
          data.right != null ? String(data.right) : undefined,
          data.expiry != null ? String(data.expiry) : undefined
        );
      }
    }
  });

  const refreshPositions = useCallback(async () => {
    setLoading(true);
    try {
      const result = await positionsApi.getAll();
      setPositions(result);
    } catch (err) {
      console.error("Failed to fetch positions:", err);
    } finally {
      setLoading(false);
    }
  }, [setPositions, setLoading]);

  const closePosition = useCallback(
    async (symbol: string, strike?: number, right?: string) => {
      await positionsApi.close(symbol, strike, right);
    },
    []
  );

  const closeAll = useCallback(async () => {
    await positionsApi.closeAll();
  }, []);

  return {
    positions,
    closedPositions,
    loading,
    refreshPositions,
    closePosition,
    closeAll,
  };
}
