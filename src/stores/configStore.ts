import { create } from "zustand";
import type { TradingConfig, AppSettings } from "@/lib/types";

interface ConfigState {
  tradingConfig: TradingConfig | null;
  settings: AppSettings;
  configLoaded: boolean;

  setTradingConfig: (config: TradingConfig) => void;
  updateTradingConfig: (updates: Partial<TradingConfig>) => void;
  setSettings: (settings: AppSettings) => void;
  updateSettings: (updates: Partial<AppSettings>) => void;
  setConfigLoaded: (loaded: boolean) => void;
}

const defaultSettings: AppSettings = {
  theme: "dark",
  trading_mode: "demo",
  font_size: 16,
  show_notifications: true,
  auto_start_trading: false,
  log_level: "info",
  update_interval: 1000,
  positions_update_interval_ms: 250,
  show_charts: true,
};

export const useConfigStore = create<ConfigState>((set) => ({
  tradingConfig: null,
  settings: defaultSettings,
  configLoaded: false,

  setTradingConfig: (config) => set({ tradingConfig: config, configLoaded: true }),
  updateTradingConfig: (updates) =>
    set((state) => ({
      tradingConfig: state.tradingConfig
        ? { ...state.tradingConfig, ...updates }
        : null,
    })),
  setSettings: (settings) => set({ settings }),
  updateSettings: (updates) =>
    set((state) => ({ settings: { ...state.settings, ...updates } })),
  setConfigLoaded: (loaded) => set({ configLoaded: loaded }),
}));
