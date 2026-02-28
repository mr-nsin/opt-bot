import { useRef } from "react";
import { useTauriEvent } from "./useTauri";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useNotificationStore } from "@/stores/notificationStore";

const PNL_THROTTLE_MS = 1000;
const LOG_BATCH_MS = 150;

/**
 * Global trading event listeners.
 * Call ONCE at the app root (AppContent) to ensure sidecar events
 * are always handled regardless of which page is active.
 * PnL updates are throttled to 1s to avoid UI hang on tab switch.
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
    setDataStatus,
    setAccountMetrics,
    setSignalScanning,
  } = useTradingStore();
  const { settings } = useConfigStore();
  const { addLogsBatch } = useLogStore();
  const { addToast } = useNotificationStore();

  const logPending = useRef<Array<{ timestamp: string; level: string; category: string; message: string }>>([]);
  const logFlushScheduled = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flushLogs = () => {
    if (logPending.current.length === 0) return;
    const batch = logPending.current;
    logPending.current = [];
    logFlushScheduled.current = null;
    addLogsBatch(batch);
  };

  const pnlPending = useRef<{ realized: number; unrealized: number; total: number } | null>(null);
  const pnlFlushScheduled = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flushPnl = () => {
    if (pnlPending.current == null) return;
    const next = pnlPending.current;
    pnlPending.current = null;
    pnlFlushScheduled.current = null;
    const current = useTradingStore.getState().dailyPnl;
    if (
      current.realized === next.realized &&
      current.unrealized === next.unrealized &&
      current.total === next.total
    ) {
      return;
    }
    setDailyPnl(next);
  };

  // ---- Engine status ----
  useTauriEvent("trading:engine_status", (data: any) => {
    if (data.status) setStatus(data.status);
    if (data.connected !== undefined) setConnectedToTws(data.connected);
  });

  // ---- P&L updates (throttled to 1s; first update flushes immediately so UI shows value right away) ----
  useTauriEvent("trading:pnl_update", (data: any) => {
    const next = {
      realized: data.realized_pnl ?? 0,
      unrealized: data.unrealized_pnl ?? 0,
      total: data.daily_pnl ?? 0,
    };
    pnlPending.current = next;
    if (pnlFlushScheduled.current == null) {
      flushPnl();
      pnlFlushScheduled.current = setTimeout(() => {
        flushPnl();
        pnlFlushScheduled.current = null;
      }, PNL_THROTTLE_MS);
    }
  });

  // ---- IBKR account metrics; only update store if values changed (shallow compare) ----
  useTauriEvent("trading:account_metrics", (data: any) => {
    if (data && typeof data === "object" && !Array.isArray(data)) {
      const metrics: Record<string, number> = {};
      for (const [k, v] of Object.entries(data)) {
        if (typeof v === "number" && !Number.isNaN(v)) metrics[k] = v;
        if (typeof v === "string" && v.trim() !== "") {
          const n = Number(v);
          if (!Number.isNaN(n)) metrics[k] = n;
        }
      }
      if (Object.keys(metrics).length === 0) return;
      const current = useTradingStore.getState().accountMetrics;
      if (current && Object.keys(current).length === Object.keys(metrics).length) {
        let same = true;
        for (const [k, v] of Object.entries(metrics)) {
          if (current[k] !== v) {
            same = false;
            break;
          }
        }
        if (same) return;
      }
      setAccountMetrics(metrics);
    }
  });

  // ---- Log messages from the sidecar (batched to avoid UI hang when many entries) ----
  useTauriEvent("trading:log_message", (data: any) => {
    const ts = data.timestamp || new Date().toISOString();
    const category = data.category || "trading";
    const message = data.message || "";

    logPending.current.push({
      timestamp: ts,
      level: data.level || "INFO",
      category,
      message,
    });
    if (logFlushScheduled.current == null) {
      logFlushScheduled.current = setTimeout(() => {
        flushLogs();
      }, LOG_BATCH_MS);
    }

    if (
      category === "signal" &&
      message.toLowerCase().includes("signal scanner active")
    ) {
      setSignalScanning(true, ts);
    }
  });

  // ---- Data feed status (every ~10s when running) ----
  useTauriEvent("trading:data_status", (data: any) => {
    if (data && typeof data.connected === "boolean") {
      setDataStatus({
        timestamp: data.timestamp || new Date().toISOString(),
        connected: data.connected,
        data_feed_started: !!data.data_feed_started,
        symbols: Array.isArray(data.symbols) ? data.symbols : [],
        event_queue_size: typeof data.event_queue_size === "number" ? data.event_queue_size : 0,
        tick_subscriptions: typeof data.tick_subscriptions === "number" ? data.tick_subscriptions : 0,
        stock_ticks_sample: Array.isArray(data.stock_ticks_sample) ? data.stock_ticks_sample : [],
        history_bars_count: typeof data.history_bars_count === "number" ? data.history_bars_count : 0,
      });
    }
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

  // ---- Engine / protocol errors ----
  useTauriEvent("trading:error", (data: any) => {
    const message =
      data?.message ||
      data?.error?.message ||
      "Trading engine error. Check Logs for details.";

    setStatus({ Error: message });

    if (settings.show_notifications) {
      addToast({
        title: "Trading Engine Error",
        message,
        type: "error",
      });
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
    setSignalScanning(false);

    if (settings.show_notifications) {
      addToast({
        title: "Engine Stopped",
        message: "Trading engine process has terminated",
        type: "warning",
      });
    }
  });
}
