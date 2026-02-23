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

  // Actions
  setStatus: (status: TradingStatus) => void;
  setSidecarRunning: (running: boolean) => void;
  setConnectedToTws: (connected: boolean) => void;
  setDailyPnl: (pnl: DailyPnL) => void;
  setTradeStats: (total: number, wins: number, losses: number) => void;
  setLastSignal: (signal: SignalEvent | null) => void;
  addTrade: (trade: TradeRecord) => void;
  setDataStatus: (data: DataStatus | null) => void;
  setAccountMetrics: (metrics: AccountMetrics | null) => void;
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
  setDataStatus: (data) => set({ dataStatus: data }),
  setAccountMetrics: (metrics) => set({ accountMetrics: metrics }),
  reset: () => set(initialState),
}));
