import { invoke } from "@tauri-apps/api/core";

/** Trading config: get / save */
export const config = {
  get: () => invoke<unknown>("get_config"),
  save: (cfg: unknown) => invoke<string>("save_config", { config: cfg }),
  getSettings: () => invoke<unknown>("get_settings"),
  saveSettings: (settings: unknown) => invoke<string>("save_settings", { settings }),
  getSettingsFile: () => invoke<unknown>("get_settings_file"),
};

/** Logs: get (level?, category?, limit?), clear, getStats */
export const logs = {
  get: (level?: string | null, category?: string | null, limit?: number) =>
    invoke<unknown[]>("get_logs", { level: level ?? null, category: category ?? null, limit: limit ?? null }),
  clear: () => invoke<string>("clear_logs"),
  getStats: () => invoke<unknown>("get_log_stats"),
};

/** Trading: start, stop, emergencyStop, getStatus, getAccountMetrics */
export const trading = {
  start: (cfg: unknown) => invoke<string>("start_trading", { config: cfg }),
  stop: () => invoke<string>("stop_trading"),
  emergencyStop: () => invoke<string>("emergency_stop"),
  getStatus: () =>
    invoke<{
      status: string;
      sidecar_running: boolean;
      connected_to_tws: boolean;
      daily_pnl: number;
      total_trades: number;
      winning_trades: number;
      losing_trades: number;
    }>("get_trading_status"),
  getAccountMetrics: () => invoke<Record<string, number> | null>("get_account_metrics"),
  simulateDemo: () => invoke<string>("simulate_demo"),
};

/** Positions: getAll, close(symbol), closeAll */
export const positions = {
  getAll: () => invoke<unknown[]>("get_positions"),
  close: (symbol: string, strike?: number, right?: string) =>
    invoke<string>("close_position", { symbol, strike, right }),
  closeAll: () => invoke<string>("close_all_positions"),
};

/** App lifecycle */
export const app = {
  confirmClose: () => invoke<void>("confirm_close"),
};

/** License: validate, getStatus, activate(key, email), deactivate, getHardwareId, getLicenseInfo */
export const license = {
  validate: () => invoke<unknown>("validate_license"),
  getStatus: () => invoke<unknown>("get_license_status"),
  activate: (key: string, email: string) => invoke<unknown>("activate_license", { key, email }),
  deactivate: () => invoke<void>("deactivate_license"),
  getHardwareId: () => invoke<string>("get_hardware_id"),
  getLicenseInfo: () => invoke<{ email: string; license_key: string } | null>("get_license_info"),
};
