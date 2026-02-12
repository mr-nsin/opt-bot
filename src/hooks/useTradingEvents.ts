import { useTauriEvent } from "./useTauri";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useNotificationStore } from "@/stores/notificationStore";

/**
 * Global trading event listeners.
 * Call ONCE at the app root (AppContent) to ensure sidecar events
 * are always handled regardless of which page is active.
 */
export function useTradingEvents() {
  const {
    setStatus,
    setSidecarRunning,
    setConnectedToTws,
    setDailyPnl,
    setTradeStats,
    setLastSignal,
    addTrade,
  } = useTradingStore();
  const { settings } = useConfigStore();
  const { addLog } = useLogStore();
  const { addToast } = useNotificationStore();

  // ---- Engine status ----
  useTauriEvent("trading:engine_status", (data: any) => {
    if (data.status) setStatus(data.status);
    if (data.connected !== undefined) setConnectedToTws(data.connected);
  });

  // ---- P&L updates ----
  useTauriEvent("trading:pnl_update", (data: any) => {
    setDailyPnl({
      realized: data.realized_pnl ?? 0,
      unrealized: data.unrealized_pnl ?? 0,
      total: data.daily_pnl ?? 0,
    });
  });

  // ---- Log messages from the sidecar ----
  useTauriEvent("trading:log_message", (data: any) => {
    addLog({
      timestamp: data.timestamp || new Date().toISOString(),
      level: data.level || "INFO",
      category: data.category || "trading",
      message: data.message || "",
    });
  });

  // ---- TWS connection status ----
  useTauriEvent("trading:connection_status", (data: any) => {
    if (data.connected !== undefined) {
      setConnectedToTws(data.connected);
      if (settings.show_notifications) {
        addToast({
          title: data.connected ? "TWS Connected" : "TWS Disconnected",
          message:
            data.message ||
            (data.connected ? "Connected to TWS" : "Connection lost"),
          type: data.connected ? "success" : "warning",
        });
      }
    }
  });

  // ---- Trade executed ----
  useTauriEvent("trading:trade_executed", (data: any) => {
    addTrade({
      id: data.id || Date.now(),
      symbol: data.symbol || "",
      right: data.right || "",
      strike: data.strike || 0,
      expiry: data.expiry || "",
      side: data.side || "BUY",
      quantity: data.quantity || 0,
      entry_price: data.entry_price || data.price || 0,
      status: "open",
      timestamp: data.timestamp || new Date().toISOString(),
    });

    const state = useTradingStore.getState();
    setTradeStats(
      state.totalTrades + 1,
      state.winningTrades,
      state.losingTrades
    );

    if (settings.show_notifications) {
      addToast({
        title: "Trade Executed",
        message: `${data.side || "BUY"} ${data.symbol || ""} ${data.right || ""} ${data.strike || ""} x${data.quantity || 0}`,
        type: "info",
      });
    }
  });

  // ---- Trade closed ----
  useTauriEvent("trading:trade_closed", (data: any) => {
    const pnl = data.pnl || 0;
    const state = useTradingStore.getState();

    if (pnl > 0) {
      setTradeStats(
        state.totalTrades,
        state.winningTrades + 1,
        state.losingTrades
      );
    } else if (pnl < 0) {
      setTradeStats(
        state.totalTrades,
        state.winningTrades,
        state.losingTrades + 1
      );
    }

    if (settings.show_notifications) {
      addToast({
        title: "Trade Closed",
        message: `${data.symbol || ""} P&L: $${Number(pnl).toFixed(2)}`,
        type: pnl >= 0 ? "success" : "error",
      });
    }
  });

  // ---- Signal detected ----
  useTauriEvent("trading:signal_detected", (data: any) => {
    setLastSignal({
      symbol: data.symbol || "",
      signal_type: data.signal_type || "CALL",
      strike: data.strike || 0,
      price: data.price || 0,
      timestamp: data.timestamp || new Date().toISOString(),
      reason: data.reason || "",
    });

    if (settings.show_notifications) {
      addToast({
        title: "Signal Detected",
        message: `${data.signal_type || "CALL"} on ${data.symbol || ""} @ ${data.strike || 0}`,
        type: "info",
      });
    }
  });

  // ---- Sidecar process terminated ----
  useTauriEvent("sidecar-terminated", () => {
    setSidecarRunning(false);
    setStatus("Idle");
    setConnectedToTws(false);

    if (settings.show_notifications) {
      addToast({
        title: "Engine Stopped",
        message: "Trading engine process has terminated",
        type: "warning",
      });
    }
  });
}
