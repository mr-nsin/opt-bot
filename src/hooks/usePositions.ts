import { useCallback } from "react";
import { positions as positionsApi } from "@/lib/tauri-commands";
import { usePositionStore, positionKey } from "@/stores/positionStore";
import type { Position } from "@/lib/types";

export function usePositions() {
  const { positions, closedPositions, loading, setPositions, setLoading } =
    usePositionStore();

  // position_update and trade_closed listeners moved to useTradingEvents (app-level)
  // so positions update regardless of which page is active

  const refreshPositions = useCallback(async () => {
    setLoading(true);
    try {
      const result = await positionsApi.getAll();
      setPositions(result as Position[]);
    } catch (err) {
      console.error("Failed to fetch positions:", err);
    } finally {
      setLoading(false);
    }
  }, [setPositions, setLoading]);

  const closePosition = useCallback(
    async (symbol: string, strike?: number, right?: string, expiry?: string) => {
      const key = positionKey(symbol, strike, right, expiry);
      const store = usePositionStore.getState();
      // Prevent duplicate close requests
      if (store.closingPositions.has(key)) return;
      store.setClosing(key, true);
      try {
        await positionsApi.close(symbol, strike, right, expiry);
      } catch (err) {
        // Clear closing state on error so user can retry
        usePositionStore.getState().setClosing(key, false);
        console.error("Failed to close position:", err);
      }
    },
    []
  );

  const closeAll = useCallback(async () => {
    await positionsApi.closeAll();
  }, []);

  const closeCalls = useCallback(async () => {
    await positionsApi.closeCalls();
  }, []);

  const closePuts = useCallback(async () => {
    await positionsApi.closePuts();
  }, []);

  return {
    positions,
    closedPositions,
    loading,
    refreshPositions,
    closePosition,
    closeAll,
    closeCalls,
    closePuts,
  };
}
