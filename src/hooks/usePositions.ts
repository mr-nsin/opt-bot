import { useCallback, useEffect } from "react";
import { positions as positionsApi } from "@/lib/tauri-commands";
import { usePositionStore } from "@/stores/positionStore";
import { useTauriEvent } from "./useTauri";
import type { Position } from "@/lib/types";

export function usePositions() {
  const { positions, closedPositions, loading, setPositions, updatePosition, removePosition, addClosedPosition, setLoading } =
    usePositionStore();

  // Listen to position updates
  useTauriEvent<Position>("trading:position_update", (data) => {
    const existing = positions.find((p) => p.symbol === data.symbol);
    if (existing) {
      updatePosition(data.symbol, data);
    } else {
      setPositions([...positions, data]);
    }
  });

  useTauriEvent("trading:trade_closed", (data: any) => {
    if (data.symbol) {
      const pos = positions.find((p) => p.symbol === data.symbol);
      if (pos) {
        addClosedPosition({ ...pos, ...data });
        removePosition(data.symbol);
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
