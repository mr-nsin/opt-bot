import { create } from "zustand";
import type { TradingStatus, DailyPnL, SignalEvent, TradeRecord, DataStatus, AccountMetrics } from "@/lib/types";

const nr = (r?: string) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);

interface TradingState {
  status: TradingStatus;
  sidecarRunning: boolean;
  connectedToTws: boolean;
  dailyPnl: DailyPnL;
  totalTrades: number;
  openTrades: number;
  closedTrades: number;
  winningTrades: number;
  losingTrades: number;
  lastSignal: SignalEvent | null;
  /** Signals detected in current session (for grid display) */
  signalsInSession: SignalEvent[];
  todayTrades: TradeRecord[];
  /** Last data feed status (updated every ~10s when engine is running) */
  dataStatus: DataStatus | null;
  /** IBKR account summary (NetLiquidation, BuyingPower, etc.); updated every ~5s when connected */
  accountMetrics: AccountMetrics | null;
  /** Whether the engine is actively scanning for signals (heartbeat received within last 60s) */
  isSignalScanning: boolean;
  /** Timestamp of the last signal-scan heartbeat from the engine */
  lastSignalScanTime: string | null;
  /** Signal DataFrame: candle signals per stock (from initial scan after data feed starts) */
  signalData: { signals: Array<{ symbol: string; date: string; open: number; high: number; low: number; close: number; volume: number; signal: string }>; system_started_at: string; timestamp: string } | null;

  /** Live market data keyed by symbol (bid/ask/last) */
  marketData: Record<string, { symbol: string; last: number; bid: number; ask: number }>;

  // Actions
  setStatus: (status: TradingStatus) => void;
  setSidecarRunning: (running: boolean) => void;
  setConnectedToTws: (connected: boolean) => void;
  setDailyPnl: (pnl: DailyPnL) => void;
  setTradeStats: (total: number, wins: number, losses: number) => void;
  setOpenClosedTrades: (open: number, closed: number) => void;
  setLastSignal: (signal: SignalEvent | null) => void;
  addSignalToSession: (signal: SignalEvent) => void;
  clearSignalsInSession: () => void;
  addTrade: (trade: TradeRecord) => void;
  /** Update the first matching open trade with PnL when position is closed */
  updateTradePnl: (match: { symbol?: string; right?: string; strike?: number; expiry?: string }, pnl: number, exitPrice?: number) => void;
  setDataStatus: (data: DataStatus | null) => void;
  setAccountMetrics: (metrics: AccountMetrics | null) => void;
  /** Mark the engine as actively signal-scanning (called when heartbeat log is received) */
  setSignalScanning: (scanning: boolean, timestamp?: string) => void;
  setSignalData: (data: { signals: Array<{ symbol: string; date: string; open: number; high: number; low: number; close: number; volume: number; signal: string }>; system_started_at: string; timestamp: string } | null) => void;
  reset: () => void;
  /** Mark all open trades as closed (emergency stop; PnL unknown) */
  markOpenTradesClosedOnEmergency: () => void;
  /** Hydrate todayTrades from backend (e.g. on page load when engine already running) */
  setTodayTrades: (trades: TradeRecord[]) => void;
  /** Update live tick data for a symbol (from tick_batch events) */
  updateTickData: (tick: { symbol: string; last: number; bid: number; ask: number }) => void;
}

const initialState = {
  status: "Idle" as TradingStatus,
  sidecarRunning: false,
  connectedToTws: false,
  dailyPnl: { realized: 0, unrealized: 0, total: 0 },
  totalTrades: 0,
  openTrades: 0,
  closedTrades: 0,
  winningTrades: 0,
  losingTrades: 0,
  lastSignal: null,
  signalsInSession: [] as SignalEvent[],
  todayTrades: [] as TradeRecord[],
  dataStatus: null as DataStatus | null,
  accountMetrics: null as AccountMetrics | null,
  isSignalScanning: false,
  lastSignalScanTime: null as string | null,
  signalData: null as { signals: Array<{ symbol: string; date: string; open: number; high: number; low: number; close: number; volume: number; signal: string }>; system_started_at: string; timestamp: string } | null,
  marketData: {} as Record<string, { symbol: string; last: number; bid: number; ask: number }>,
};

export const useTradingStore = create<TradingState>((set) => ({
  ...initialState,

  setStatus: (status) => set({ status }),
  setSidecarRunning: (running) => set({ sidecarRunning: running }),
  setConnectedToTws: (connected) => set({ connectedToTws: connected }),
  setDailyPnl: (pnl) => set({ dailyPnl: pnl }),
  setTradeStats: (total, wins, losses) =>
    set({ totalTrades: total, winningTrades: wins, losingTrades: losses }),
  setOpenClosedTrades: (open, closed) =>
    set({ openTrades: open, closedTrades: closed }),
  setLastSignal: (signal) => set({ lastSignal: signal }),
  addSignalToSession: (signal) =>
    set((state) => ({
      signalsInSession: [signal, ...state.signalsInSession].slice(0, 100),
    })),
  clearSignalsInSession: () => set({ signalsInSession: [] }),
  addTrade: (trade) =>
    set((state) => ({ todayTrades: [trade, ...state.todayTrades].slice(0, 100) })),
  updateTradePnl: (match, pnl, exitPrice) =>
    set((state) => {
      const normExp = (e?: string) => (e || "").replace(/-/g, "").trim();
      const idx = state.todayTrades.findIndex(
        (t) =>
          (t.status === "open" || t.status === undefined) &&
          (match.symbol == null || t.symbol === match.symbol) &&
          (match.right == null || nr(t.right) === nr(match.right)) &&
          (match.strike == null || Number(t.strike) === match.strike) &&
          (match.expiry == null || match.expiry === "" || normExp(t.expiry) === normExp(match.expiry))
      );
      if (idx < 0) return state;
      const next = [...state.todayTrades];
      next[idx] = { ...next[idx], pnl, status: "closed", exit_price: exitPrice };
      return { todayTrades: next };
    }),
  setDataStatus: (data) => set({ dataStatus: data }),
  setAccountMetrics: (metrics) => set({ accountMetrics: metrics }),
  setSignalScanning: (scanning, timestamp) =>
    set({
      isSignalScanning: scanning,
      lastSignalScanTime: timestamp ?? new Date().toISOString(),
    }),
  setSignalData: (data) => set({ signalData: data }),
  reset: () =>
    set({
      ...initialState,
      signalsInSession: [] as SignalEvent[],
      signalData: null,
    }),
  markOpenTradesClosedOnEmergency: () =>
    set((state) => ({
      todayTrades: state.todayTrades.map((t) =>
        t.status === "open" || t.status === undefined
          ? { ...t, status: "closed" as const, pnl: undefined, exit_price: undefined }
          : t
      ),
      openTrades: 0,
      closedTrades: state.totalTrades,
      dailyPnl: {
        ...state.dailyPnl,
        unrealized: 0,
        total: state.dailyPnl.realized,
      },
    })),
  setTodayTrades: (trades) =>
    set({ todayTrades: Array.isArray(trades) ? trades.slice(0, 100) : [] }),
  updateTickData: (tick) =>
    set((state) => ({
      marketData: { ...state.marketData, [tick.symbol]: tick },
    })),
}));
