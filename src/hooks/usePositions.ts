import { useCallback } from "react";
import { positions as positionsApi } from "@/lib/tauri-commands";
import { usePositionStore, positionRowKey } from "@/stores/positionStore";
import type { Position } from "@/lib/types";

export function usePositions() {
  const { positions, closedPositions, loading, setPositions, setLoading } =
    usePositionStore();

  // position_update and trade_closed listeners moved to useTradingEvents (app-level)
  // so positions update regardless of which page is active

  const refreshPositions = useCallback(async () => {
    setLoading(true);
    try {
      const result = (await positionsApi.getAll()) as Position[];
      const apiList = Array.isArray(result) ? result : [];
      const local = usePositionStore.getState().positions;
      // TWS can lag behind entry fills. API may omit a row that trade_executed already added.
      // Merge: prefer API for each key; keep local open rows whose keys are missing from API.
      const apiKeys = new Set(apiList.map((p) => positionRowKey(p)));
      const orphans = local.filter(
        (p) => (p.quantity ?? 0) > 0 && !apiKeys.has(positionRowKey(p))
      );
      setPositions([...apiList, ...orphans]);
    } catch (err) {
      console.error("Failed to fetch positions:", err);
    } finally {
      setLoading(false);
    }
  }, [setPositions, setLoading]);

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
    closePosition,
    closeAll,
    closeCalls,
    closePuts,
  };
}
