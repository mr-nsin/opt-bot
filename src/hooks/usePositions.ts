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
    const existing = current.find(
      (p) => p.symbol === data.symbol && p.strike === data.strike && p.right === data.right
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
      const pos = current.find(
        (p) =>
          p.symbol === data.symbol &&
          (data.strike == null || Number(p.strike) === Number(data.strike)) &&
          (data.right == null || p.right === data.right)
      );
      if (pos) {
        addClosedPosition({ ...pos, ...data });
        removePosition(
          data.symbol,
          data.strike != null ? Number(data.strike) : undefined,
          data.right != null ? String(data.right) : undefined
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
    async (symbol: string) => {
      await positionsApi.close(symbol);
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
