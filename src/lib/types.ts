export interface LogEntry {
  timestamp: string;
  level: string;
  category: string;
  message: string;
}

export interface AppSettings {
  theme: string;
  trading_mode: string;
  font_size: number;
  show_notifications: boolean;
  auto_start_trading: boolean;
  log_level: string;
  update_interval: number;
  show_charts: boolean;
}

export interface TradingConfig {
  profit_increment?: number;
  expiry_to_trade?: string;
  spy_qqq_expiry?: string;
  use_diff_expiry_index?: string;
  ip?: string;
  port?: number;
  client_id?: number;
  account_id?: string;
  market_start_time?: string;
  script_start_time?: string;
  script_end_time?: string;
  vwap_on_off?: string;
  order_transmit?: boolean;
  use_timer_in_order?: string;
  order_expiry_timer?: number;
  call_delta_check?: number;
  put_delta_check?: number;
  volume_check?: number;
  atr_checks?: number;
  active_volume?: number;
  max_contract_amount?: number;
  atr_value?: number;
  share_volume?: number;
  body?: number;
  midpoint_offset?: number;
  quantity?: number;
  fetch_value?: string;
  candle_time?: string;
  distance_between_trade?: number;
  emergency_close_buffer_seconds?: number;
  avg_volumes_candles?: number;
  stock_data?: Record<string, { amount: number }>;
  stock_list_to_trade?: Record<string, string>;
  per_day_trades?: number;
  loss_amount_day?: number;
  profit_amount_day?: number;
}

export type TradingStatus = "Idle" | "Starting" | "Running" | "Stopping" | { Error: string };

export interface DailyPnL {
  realized: number;
  unrealized: number;
  total: number;
}

export interface SignalEvent {
  symbol?: string;
  direction?: string;
  [key: string]: unknown;
}

export interface TradeRecord {
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
  [key: string]: unknown;
}

export interface DataStatus {
  [key: string]: unknown;
}

/** IBKR account summary: tag -> numeric value (e.g. NetLiquidation, BuyingPower). */
export type AccountMetrics = Record<string, number>;

export interface Position {
  symbol: string;
  type?: string;
  right?: string;
  strike?: number;
  expiry?: string;
  qty?: number;
  quantity?: number;
  avg_price?: number;
  current_price?: number;
  entry_price?: number;
  exit_price?: number;
  pnl?: number;
  pnl_percent?: number;
  profit_price?: number;
  stoploss_price?: number;
  trailing_active?: boolean;
  /** Bid price (used for TP/SL when available) */
  bid?: number;
  /** Ask price (for display; not used in TP/SL close logic) */
  ask?: number;
  /** Last traded price */
  last?: number;
  /** Price used for TP/SL checks: bid if valid, else last */
  exit_price_used?: number;
  /** "bid" or "last" — source of exit_price_used */
  exit_price_source?: string;
  delta?: number;
  entry_time?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface LicenseStatus {
  valid: boolean;
  tier?: string;
  days_remaining?: number;
  expires_at?: string;
  features?: {
    live_trading?: boolean;
    max_symbols?: number;
    max_daily_trades?: number;
    strategies?: string[];
  };
  hardware_bound?: boolean;
  error?: string;
}

export interface PnLEvent {
  realized?: number;
  unrealized?: number;
  total?: number;
  [key: string]: unknown;
}
