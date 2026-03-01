import { create } from "zustand";
import type { TradingStatus, DailyPnL, SignalEvent, TradeRecord, DataStatus, AccountMetrics } from "@/lib/types";

interface TradingState {
  status: TradingStatus;
  sidecarRunning: boolean;
  connectedToTws: boolean;
  dailyPnl: DailyPnL;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  lastSignal: SignalEvent | null;
  todayTrades: TradeRecord[];
  /** Last data feed status (updated every ~10s when engine is running) */
  dataStatus: DataStatus | null;
  /** IBKR account summary (NetLiquidation, BuyingPower, etc.); updated every ~5s when connected */
  accountMetrics: AccountMetrics | null;
  /** Whether the engine is actively scanning for signals (heartbeat received within last 60s) */
  isSignalScanning: boolean;
  /** Timestamp of the last signal-scan heartbeat from the engine */
  lastSignalScanTime: string | null;

  // Actions
  setStatus: (status: TradingStatus) => void;
  setSidecarRunning: (running: boolean) => void;
  setConnectedToTws: (connected: boolean) => void;
  setDailyPnl: (pnl: DailyPnL) => void;
  setTradeStats: (total: number, wins: number, losses: number) => void;
  setLastSignal: (signal: SignalEvent | null) => void;
  addTrade: (trade: TradeRecord) => void;
  /** Update the first matching open trade with PnL when position is closed */
  updateTradePnl: (match: { symbol?: string; right?: string; strike?: number }, pnl: number, exitPrice?: number) => void;
  setDataStatus: (data: DataStatus | null) => void;
  setAccountMetrics: (metrics: AccountMetrics | null) => void;
  /** Mark the engine as actively signal-scanning (called when heartbeat log is received) */
  setSignalScanning: (scanning: boolean, timestamp?: string) => void;
  reset: () => void;
}

const initialState = {
  status: "Idle" as TradingStatus,
  sidecarRunning: false,
  connectedToTws: false,
  dailyPnl: { realized: 0, unrealized: 0, total: 0 },
  totalTrades: 0,
  winningTrades: 0,
  losingTrades: 0,
  lastSignal: null,
  todayTrades: [] as TradeRecord[],
  dataStatus: null as DataStatus | null,
  accountMetrics: null as AccountMetrics | null,
  isSignalScanning: false,
  lastSignalScanTime: null as string | null,
};

export const useTradingStore = create<TradingState>((set) => ({
  ...initialState,

  setStatus: (status) => set({ status }),
  setSidecarRunning: (running) => set({ sidecarRunning: running }),
  setConnectedToTws: (connected) => set({ connectedToTws: connected }),
  setDailyPnl: (pnl) => set({ dailyPnl: pnl }),
  setTradeStats: (total, wins, losses) =>
    set({ totalTrades: total, winningTrades: wins, losingTrades: losses }),
  setLastSignal: (signal) => set({ lastSignal: signal }),
  addTrade: (trade) =>
    set((state) => ({ todayTrades: [trade, ...state.todayTrades].slice(0, 100) })),
  updateTradePnl: (match, pnl, exitPrice) =>
    set((state) => {
      const idx = state.todayTrades.findIndex(
        (t) =>
          (t.status === "open" || t.status === undefined) &&
          (match.symbol == null || t.symbol === match.symbol) &&
          (match.right == null || t.right === match.right) &&
          (match.strike == null || Number(t.strike) === match.strike)
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
  reset: () => set(initialState),
}));
