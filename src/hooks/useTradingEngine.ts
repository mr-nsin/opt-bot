import { useCallback } from "react";
import { config, trading } from "@/lib/tauri-commands";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";

/**
 * Trading engine actions (start / stop / emergency stop).
 * Event listeners are in useTradingEvents hook (called once at app root).
 */
export function useTradingEngine() {
  const {
    status,
    sidecarRunning,
    setStatus,
    setSidecarRunning,
    setConnectedToTws,
    setDailyPnl,
    setTradeStats,
    setOpenClosedTrades,
    setTodayTrades,
    clearSignalsInSession,
  } = useTradingStore();
  const { tradingConfig, settings } = useConfigStore();

  const startTrading = useCallback(async () => {
    if (!tradingConfig) throw new Error("Configuration not loaded");
    setStatus("Starting");
    clearSignalsInSession();
    try {
      // Persist config before start so account_id and all params are saved
      await config.save(tradingConfig);
      const enginePayload = {
        ...tradingConfig,
        ui: {
          positions_update_interval_ms: settings.positions_update_interval_ms ?? 250,
        },
      };
      const result = await trading.start(enginePayload);
      setStatus("Running");
      setSidecarRunning(true);
      return result;
    } catch (err) {
      setStatus({ Error: String(err) });
      throw err;
    }
  }, [tradingConfig, settings.positions_update_interval_ms, setStatus, setSidecarRunning, clearSignalsInSession]);

  const stopTrading = useCallback(async () => {
    setStatus("Stopping");
    try {
      const result = await trading.stop();
      setStatus("Idle");
      setSidecarRunning(false);
      setConnectedToTws(false);
      return result;
    } catch (err) {
      setStatus({ Error: String(err) });
      throw err;
    }
  }, [setStatus, setSidecarRunning, setConnectedToTws]);

  const emergencyStop = useCallback(async () => {
    try {
      const result = await trading.emergencyStop();
      setStatus("Idle");
      setSidecarRunning(false);
      setConnectedToTws(false);
      return result;
    } catch (err) {
      setStatus({ Error: String(err) });
      throw err;
    }
  }, [setStatus, setSidecarRunning, setConnectedToTws]);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await trading.getStatus();
      setStatus(data.status);
      setSidecarRunning(data.sidecar_running);
      setConnectedToTws(data.connected_to_tws);
      setDailyPnl(typeof data.daily_pnl === "object" ? data.daily_pnl : { realized: 0, unrealized: 0, total: data.daily_pnl });
      setTradeStats(data.total_trades, data.winning_trades, data.losing_trades);
      setOpenClosedTrades(data.open_trades ?? 0, data.closed_trades ?? 0);
      if (Array.isArray(data.trades_today)) {
        setTodayTrades(
          data.trades_today.map((t) => ({
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
  }, [setStatus, setSidecarRunning, setConnectedToTws, setDailyPnl, setTradeStats, setOpenClosedTrades, setTodayTrades]);

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
