import { useCallback } from "react";
import { config, trading } from "@/lib/tauri-commands";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";

/**
 * Trading engine actions (start / stop / emergency stop).
 * Event listeners are in useTradingEvents hook (called once at app root).
 */
export function useTradingEngine() {
  const status = useTradingStore((s) => s.status);
  const sidecarRunning = useTradingStore((s) => s.sidecarRunning);
  const tradingConfig = useConfigStore((s) => s.tradingConfig);
  const getActions = () => useTradingStore.getState();

  const startTrading = useCallback(async () => {
    if (!tradingConfig) throw new Error("Configuration not loaded");
    const a = getActions();
    a.setStatus("Starting");
    a.clearSignalsInSession();
    try {
      await config.save(tradingConfig);
      const result = await trading.start(tradingConfig);
      getActions().setStatus("Running");
      getActions().setSidecarRunning(true);
      return result;
    } catch (err) {
      getActions().setStatus({ Error: String(err) });
      throw err;
    }
  }, [tradingConfig]);

  const stopTrading = useCallback(async () => {
    getActions().setStatus("Stopping");
    try {
      const result = await trading.stop();
      const a = getActions();
      a.setStatus("Idle");
      a.setSidecarRunning(false);
      a.setConnectedToTws(false);
      return result;
    } catch (err) {
      getActions().setStatus({ Error: String(err) });
      throw err;
    }
  }, []);

  const emergencyStop = useCallback(async () => {
    try {
      const result = await trading.emergencyStop();
      const a = getActions();
      a.setStatus("Idle");
      a.setSidecarRunning(false);
      a.setConnectedToTws(false);
      return result;
    } catch (err) {
      getActions().setStatus({ Error: String(err) });
      throw err;
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await trading.getStatus();
      const a = getActions();
      a.setStatus(data.status as any);
      a.setSidecarRunning(data.sidecar_running);
      a.setConnectedToTws(data.connected_to_tws);
      a.setDailyPnl(typeof data.daily_pnl === "object" ? data.daily_pnl : { realized: 0, unrealized: 0, total: data.daily_pnl });
      a.setTradeStats(data.total_trades, data.winning_trades, data.losing_trades);
      a.setOpenClosedTrades(data.open_trades ?? 0, data.closed_trades ?? 0);
      if (Array.isArray(data.trades_today)) {
        a.setTodayTrades(
          data.trades_today.map((t: any) => ({
            id: t.id,
            symbol: t.symbol,
            right: t.right,
            strike: t.strike,
            expiry: t.expiry,
            side: t.side,
            quantity: t.quantity,
            entry_price: t.entry_price,
            exit_price: t.exit_price,
            pnl: t.pnl,
            status: t.status,
            timestamp: t.timestamp,
          }))
        );
      }
    } catch (err) {
      console.error("Failed to refresh status:", err);
    }
  }, []);

  return {
    status,
    startTrading,
    stopTrading,
    emergencyStop,
    refreshStatus,
    isRunning: status === "Running",
    isIdle: status === "Idle",
    sidecarRunning,
    canStop: status === "Running" || sidecarRunning,
  };
}
