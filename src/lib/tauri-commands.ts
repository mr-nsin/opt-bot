import { invoke } from "@tauri-apps/api/core";

/** Trading config: get / save */
export const config = {
  get: () => invoke<unknown>("get_config"),
  save: (cfg: unknown) => invoke<string>("save_config", { config: cfg }),
  getSettings: () => invoke<unknown>("get_settings"),
  saveSettings: (settings: unknown) => invoke<string>("save_settings", { settings }),
  getSettingsFile: () => invoke<unknown>("get_settings_file"),
};

/** Logs: pushLogEntry, get (level?, category?, limit?), getLogsDir, clear, getStats */
export const logs = {
  pushLogEntry: (message: string, level?: string, category?: string) =>
    invoke<void>("push_log_entry", { message, level: level ?? null, category: category ?? null }),
  get: (level?: string | null, category?: string | null, limit?: number) =>
    invoke<unknown[]>("get_logs", { level: level ?? null, category: category ?? null, limit: limit ?? null }),
  getLogsDir: () => invoke<string>("get_logs_dir"),
  clear: () => invoke<string>("clear_logs"),
  getStats: () => invoke<unknown>("get_log_stats"),
};

/** Trading: start, stop, emergencyStop, getStatus, getAccountMetrics */
export const trading = {
  start: (cfg: unknown) => invoke<string>("start_trading", { config: cfg }),
  stop: () => invoke<string>("stop_trading"),
  emergencyStop: (reason?: string) =>
    invoke<string>("emergency_stop", { reason: reason ?? null }),
  getStatus: () =>
    invoke<{
      status: string;
      sidecar_running: boolean;
      connected_to_tws: boolean;
      daily_pnl: number | { realized: number; unrealized: number; total: number };
      total_trades: number;
      open_trades: number;
      closed_trades: number;
      winning_trades: number;
      losing_trades: number;
      trades_today?: Array<{
        id?: number;
        symbol?: string;
        right?: string;
        strike?: number;
        expiry?: string;
        side?: string;
        quantity?: number;
        entry_price?: number;
        exit_price?: number;
        pnl?: number;
        status?: string;
        timestamp?: string;
      }>;
    }>("get_trading_status"),
  getAccountMetrics: () => invoke<Record<string, number> | null>("get_account_metrics"),
  getSignalData: () =>
    invoke<{ signals: SignalRow[]; system_started_at: string; timestamp: string } | null>("get_signal_data"),
  simulateDemo: () => invoke<string>("simulate_demo"),
};

export type SignalRow = {
  symbol: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  signal: string;
};

/** Positions: getAll, close(symbol), closeAll, closeCalls, closePuts */
export const positions = {
  getAll: () => invoke<unknown[]>("get_positions"),
  close: (symbol: string, strike?: number, right?: string, expiry?: string) =>
    invoke<string>("close_position", { symbol, strike, right, expiry }),
  closeAll: () => invoke<string>("close_all_positions"),
  closeCalls: () => invoke<string>("close_calls_positions"),
  closePuts: () => invoke<string>("close_puts_positions"),
};

/** App lifecycle */
export const app = {
  confirmClose: () => invoke<void>("confirm_close"),
};

/** License: validate, getStatus, activate(key, email), deactivate, invalidateLicenseState, getHardwareId, getLicenseInfo */
export const license = {
  validate: () => invoke<unknown>("validate_license"),
  getStatus: () => invoke<unknown>("get_license_status"),
  activate: (key: string, email: string) => invoke<unknown>("activate_license", { key, email }),
  deactivate: () => invoke<void>("deactivate_license"),
  invalidateLicenseState: () => invoke<void>("invalidate_license_state"),
  getHardwareId: () => invoke<string>("get_hardware_id"),
  getLicenseInfo: () => invoke<{ email: string; license_key: string } | null>("get_license_info"),
};
