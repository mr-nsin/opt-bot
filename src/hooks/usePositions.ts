import { useCallback } from "react";
import { positions as positionsApi } from "@/lib/tauri-commands";
import { usePositionStore } from "@/stores/positionStore";

/**
 * Imperative position API (refresh, close, closeAll, closeCalls, closePuts).
 * Real-time position_update and trade_closed events are handled globally
 * in useTradingEvents.ts (called once at AppContent root) to avoid
 * duplicate listeners that race and overwrite each other's P&L data.
 */
export function usePositions() {
  const positions = usePositionStore((s) => s.positions);
  const closedPositions = usePositionStore((s) => s.closedPositions);
  const loading = usePositionStore((s) => s.loading);

  const refreshPositions = useCallback(async () => {
    const store = usePositionStore.getState();
    if (store.positions.length > 0) return;
    store.setLoading(true);
    try {
      const result = await positionsApi.getAll();
      if (result.length > 0) {
        usePositionStore.getState().setPositions(result);
      }
    } catch (err) {
      console.error("Failed to fetch positions:", err);
    } finally {
      usePositionStore.getState().setLoading(false);
    }
  }, []);

  const forceRefreshPositions = useCallback(async () => {
    usePositionStore.getState().setLoading(true);
    try {
      const result = await positionsApi.getAll();
      usePositionStore.getState().setPositions(result);
    } catch (err) {
      console.error("Failed to fetch positions:", err);
    } finally {
      usePositionStore.getState().setLoading(false);
    }
  }, []);

  const closePosition = useCallback(
    async (symbol: string, strike?: number, right?: string, expiry?: string) => {
      await positionsApi.close(symbol, strike, right, expiry);
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
    forceRefreshPositions,
    closePosition,
    closeAll,
    closeCalls,
    closePuts,
  };
}
