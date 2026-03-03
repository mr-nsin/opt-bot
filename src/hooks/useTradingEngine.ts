import { useCallback } from "react";
import { trading } from "@/lib/tauri-commands";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";

/**
 * Trading engine actions (start / stop / emergency stop).
 * Event listeners are in useTradingEvents hook (called once at app root).
 */
export function useTradingEngine() {
  const {
    status,
    setStatus,
    setSidecarRunning,
    setConnectedToTws,
    setDailyPnl,
    setTradeStats,
  } = useTradingStore();
  const { tradingConfig } = useConfigStore();

  const startTrading = useCallback(async () => {
    if (!tradingConfig) throw new Error("Configuration not loaded");
    setStatus("Starting");
    try {
      const result = await trading.start(tradingConfig);
      setStatus("Running");
      setSidecarRunning(true);
      return result;
    } catch (err) {
      setStatus({ Error: String(err) });
      throw err;
    }
  }, [tradingConfig, setStatus, setSidecarRunning]);

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
      setDailyPnl(data.daily_pnl);
      setTradeStats(data.total_trades, data.winning_trades, data.losing_trades);
    } catch (err) {
      console.error("Failed to refresh status:", err);
    }
  }, [setStatus, setSidecarRunning, setConnectedToTws, setDailyPnl, setTradeStats]);

  return {
    status,
    startTrading,
    stopTrading,
    emergencyStop,
    refreshStatus,
    isRunning: status === "Running",
    isIdle: status === "Idle",
  };
}
