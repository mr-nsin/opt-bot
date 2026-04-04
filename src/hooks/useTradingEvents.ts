import { useRef } from "react";
import { useTauriEvent } from "./useTauri";
import { useTradingStore } from "@/stores/tradingStore";
import { usePositionStore, positionKey } from "@/stores/positionStore";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useNotificationStore } from "@/stores/notificationStore";

const PNL_THROTTLE_MS = 100;  // Flush P&L every 100ms to match position emission rate
const LOG_BATCH_MS = 150;
const POSITION_BATCH_MS = 250;  // Batch position updates per animation frame (~4/sec max)

/**
 * Global trading event listeners.
 * Call ONCE at the app root (AppContent) to ensure sidecar events
 * are always handled regardless of which page is active.
 * PnL updates are throttled to 1s to avoid UI hang on tab switch.
 */
export function useTradingEvents() {
  // Use getState() for action-only access — avoids subscribing to every tradingStore change
  const getTradingActions = () => useTradingStore.getState();
  const settings = useConfigStore((s) => s.settings);
  const addLogsBatch = useLogStore((s) => s.addLogsBatch);
  const addToast = useNotificationStore((s) => s.addToast);

  const logPending = useRef<Array<{ timestamp: string; level: string; category: string; message: string }>>([]);
  const logFlushScheduled = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Batch position updates to reduce store writes (20 events/sec → ~4 store writes/sec)
  const positionPending = useRef<Map<string, any>>(new Map());
  const positionFlushScheduled = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flushPositions = () => {
    positionFlushScheduled.current = null;
    if (positionPending.current.size === 0) return;
    const batch = new Map(positionPending.current);
    positionPending.current.clear();
    const store = usePositionStore.getState();
    const current = [...store.positions];
    let changed = false;
    for (const [key, updates] of batch) {
      const nrFn = (r?: string) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);
      const normExpFn = (e?: string) => (e || "").replace(/-/g, "").replace(/\s/g, "").trim();
      const idx = current.findIndex(
        (p) =>
          p.symbol === updates.symbol &&
          Number(p.strike) === Number(updates.strike) &&
          nrFn(p.right) === nrFn(updates.right) &&
          normExpFn(p.expiry) === normExpFn(updates.expiry)
      );
      if (idx >= 0) {
        current[idx] = { ...current[idx], ...updates };
        changed = true;
      } else if (updates.quantity > 0) {
        current.push(updates);
        changed = true;
      }
    }
    if (changed) {
      store.setPositions(current);
    }
  };

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
    getTradingActions().setDailyPnl(next);
  };

  // ---- Engine status ----
  useTauriEvent("trading:engine_status", (data: any) => {
    const actions = getTradingActions();
    if (data.status) actions.setStatus(data.status);
    if (data.connected !== undefined) actions.setConnectedToTws(data.connected);
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
      getTradingActions().setAccountMetrics(metrics);
    }
  });

  // ---- Log messages from the sidecar (supports batched entries array or single entry) ----
  useTauriEvent("trading:log_message", (data: any) => {
    const items = Array.isArray(data.entries)
      ? data.entries
      : [{ timestamp: data.timestamp, level: data.level, category: data.category, message: data.message }];

    for (const item of items) {
      const ts = item.timestamp || new Date().toISOString();
      const category = item.category || "trading";
      const message = item.message || "";

      logPending.current.push({
        timestamp: ts,
        level: item.level || "INFO",
        category,
        message,
      });

      if (
        category === "signal" &&
        message.toLowerCase().includes("signal scanner active")
      ) {
        getTradingActions().setSignalScanning(true, ts);
      }
    }
    if (logFlushScheduled.current == null) {
      logFlushScheduled.current = setTimeout(() => {
        flushLogs();
      }, LOG_BATCH_MS);
    }
  });

  // ---- Data feed status (every ~10s when running) ----
  useTauriEvent("trading:data_status", (data: any) => {
    if (data && typeof data.connected === "boolean") {
      getTradingActions().setDataStatus({
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
      getTradingActions().setConnectedToTws(data.connected);
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

    getTradingActions().setStatus({ Error: message });

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
    const actions = getTradingActions();
    actions.addTrade({
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

    // Immediately add to positionStore so Active Positions and Trade Blotter show at the same time
    const { positions, setPositions } = usePositionStore.getState();
    const nrFn = (r: string | undefined) => r === "CALL" ? "C" : r === "PUT" ? "P" : r;
    const normExp = (e?: string) => (e || "").replace(/-/g, "").replace(/\s/g, "").trim();
    const alreadyExists = positions.some(
      (p) =>
        p.symbol === (data.symbol || "") &&
        Number(p.strike) === Number(data.strike || 0) &&
        nrFn(p.right) === nrFn(data.right) &&
        normExp(p.expiry) === normExp(data.expiry)
    );
    if (!alreadyExists) {
      setPositions([...positions, {
        symbol: data.symbol || "",
        right: data.right || "",
        strike: data.strike || 0,
        expiry: data.expiry || "",
        quantity: data.quantity || 0,
        avg_price: data.entry_price || data.price || 0,
        current_price: data.entry_price || data.price || 0,
        pnl: 0,
      } as any]);
    }

    const state = useTradingStore.getState();
    const newTotal = state.totalTrades + 1;
    const closed = state.winningTrades + state.losingTrades;
    actions.setTradeStats(newTotal, state.winningTrades, state.losingTrades);
    actions.setOpenClosedTrades(newTotal - closed, closed);

    if (settings.show_notifications) {
      addToast({
        title: "Trade Executed",
        message: `${data.side || "BUY"} ${data.symbol || ""} ${data.right || ""} ${data.strike || ""} x${data.quantity || 0}`,
        type: "info",
      });
    }
  });

  // ---- Trade closed (unified: updates tradingStore stats + moves position active → closed) ----
  useTauriEvent("trading:trade_closed", (data: any) => {
    const pnl = data.pnl ?? 0;
    const state = useTradingStore.getState();

    // Update the matching open trade in todayTrades with PnL so Analytics shows it
    const closedActions = getTradingActions();
    closedActions.updateTradePnl(
      {
        symbol: data.symbol != null ? String(data.symbol) : undefined,
        right: data.right != null ? String(data.right) : undefined,
        strike: data.strike != null ? Number(data.strike) : undefined,
        expiry: data.expiry != null ? String(data.expiry) : undefined,
      },
      Number(pnl),
      data.exit_price != null ? Number(data.exit_price) : undefined
    );

    const newWins = pnl > 0 ? state.winningTrades + 1 : state.winningTrades;
    const newLosses = pnl < 0 ? state.losingTrades + 1 : state.losingTrades;
    const closed = newWins + newLosses;
    const open = state.totalTrades - closed;
    closedActions.setTradeStats(state.totalTrades, newWins, newLosses);
    closedActions.setOpenClosedTrades(Math.max(0, open), closed);

    // Move position from active → closed in positionStore
    if (data.symbol) {
      const posStore = usePositionStore.getState();
      const current = posStore.positions;
      const nrFn = (r: string | undefined) => r === "CALL" ? "C" : r === "PUT" ? "P" : r;
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      const pos = current.find(
        (p) =>
          p.symbol === data.symbol &&
          (data.strike == null || Number(p.strike) === Number(data.strike)) &&
          (data.right == null || nrFn(p.right) === nrFn(data.right)) &&
          (data.expiry == null || data.expiry === "" || normExp(p.expiry) === normExp(data.expiry))
      );
      if (pos) {
        posStore.addClosedPosition({ ...pos, ...data });
        posStore.removePosition(
          data.symbol,
          data.strike != null ? Number(data.strike) : undefined,
          data.right != null ? String(data.right) : undefined,
          data.expiry != null ? String(data.expiry) : undefined
        );
      }
    }

    if (settings.show_notifications) {
      addToast({
        title: "Trade Closed",
        message: `${data.symbol || ""} P&L: $${Number(pnl).toFixed(2)}`,
        type: pnl >= 0 ? "success" : "error",
      });
    }
  });

  // ---- Signal data (DataFrame of candle signals from initial scan) ----
  useTauriEvent("trading:signal_data", (data: any) => {
    if (data && Array.isArray(data.signals)) {
      getTradingActions().setSignalData({
        signals: data.signals,
        system_started_at: data.system_started_at ?? "",
        timestamp: data.timestamp ?? new Date().toISOString(),
      });
    }
  });

  // ---- Signal detected (no toast — only orders show notifications) ----
  useTauriEvent("trading:signal_detected", (data: any) => {
    const signalType = data.signal_type || "CALL";
    const price = data.price ?? data.strike ?? 0;
    const signal = {
      symbol: data.symbol || "",
      signal_type: signalType,
      direction: signalType,
      strike: data.strike || 0,
      price,
      expiry: data.expiry || "",
      timestamp: data.timestamp || new Date().toISOString(),
      reason: data.reason || "",
      strength: data.reason || "",
      indicator: "SuperTrend",
    };
    getTradingActions().setLastSignal(signal);
    getTradingActions().addSignalToSession(signal);
    // Notifications only for orders (trade_executed, trade_closed), not signals
  });

  // ---- Batch position snapshot (replaces all positions at once, filters recently-closed) ----
  useTauriEvent("trading:positions_snapshot", (data: any) => {
    if (!data || !Array.isArray(data.positions)) return;
    const store = usePositionStore.getState();
    // Filter out recently-closed positions and zero-price entries
    const filtered = data.positions.filter((p: any) => {
      if (!p.symbol || p.quantity <= 0) return false;
      const key = positionKey(p.symbol, p.strike, p.right, p.expiry);
      return !store.isRecentlyClosed(key);
    });
    store.setPositions(filtered);
  });

  // ---- Individual position updates (batched to reduce re-renders: 20/sec → ~4/sec) ----
  useTauriEvent("trading:position_update", (data: any) => {
    const store = usePositionStore.getState();

    const key = positionKey(data.symbol, data.strike, data.right, data.expiry);
    if (store.isRecentlyClosed(key)) return;

    // Strip zero-price fields to preserve last known good values
    const updates = { ...data };
    if (!updates.current_price || updates.current_price <= 0) {
      delete updates.current_price;
      delete updates.pnl;
      delete updates.pnl_percent;
    }
    if (updates.bid != null && updates.bid <= 0) delete updates.bid;
    if (updates.ask != null && updates.ask <= 0) delete updates.ask;
    if (updates.last != null && updates.last <= 0) delete updates.last;

    // Merge into pending batch (latest values win per key)
    const existing = positionPending.current.get(key);
    positionPending.current.set(key, existing ? { ...existing, ...updates } : updates);

    if (positionFlushScheduled.current == null) {
      positionFlushScheduled.current = setTimeout(flushPositions, POSITION_BATCH_MS);
    }
  });

  // (trade_closed position removal is handled in the unified handler above)

  // ---- Sidecar process terminated ----
  useTauriEvent("sidecar-terminated", (payload: { reason?: string } | number | null) => {
    // Flush any pending logs before resetting
    if (logFlushScheduled.current != null) {
      clearTimeout(logFlushScheduled.current);
      logFlushScheduled.current = null;
    }
    flushLogs();

    // Discard any further buffered logs that arrive after termination
    logPending.current = [];

    const termActions = getTradingActions();
    termActions.setSidecarRunning(false);
    termActions.setStatus("Idle");
    termActions.setConnectedToTws(false);
    termActions.setSignalScanning(false);

    // Emergency stop: clear positions, mark open trades closed, reset unrealized PnL
    const reason = payload && typeof payload === "object" && "reason" in payload ? payload.reason : undefined;
    if (reason === "emergency_stop") {
      usePositionStore.getState().clearAll();
      useTradingStore.getState().markOpenTradesClosedOnEmergency();
    }

    if (settings.show_notifications) {
      addToast({
        title: "Engine Stopped",
        message: "Trading engine process has terminated",
        type: "warning",
      });
    }
  });
}
