use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub strike: f64,
    pub right: String,
    pub expiry: String,
    pub quantity: i32,
    pub avg_price: f64,
    pub current_price: f64,
    pub pnl: f64,
    pub pnl_percent: f64,
    #[serde(default)]
    pub profit_price: Option<f64>,
    #[serde(default)]
    pub initial_profit_price: Option<f64>,
    #[serde(default)]
    pub stoploss_price: Option<f64>,
    #[serde(default)]
    pub effective_stoploss_price: Option<f64>,
    #[serde(default)]
    pub trailing_active: Option<bool>,
    #[serde(default)]
    pub bid: Option<f64>,
    #[serde(default)]
    pub ask: Option<f64>,
    #[serde(default)]
    pub last: Option<f64>,
    #[serde(default)]
    pub exit_price_used: Option<f64>,
    #[serde(default)]
    pub exit_price_source: Option<String>,
    /// Underlying (stock) ATR at entry; used with config to derive option TP/SL width.
    #[serde(default)]
    pub underlying_atr: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyPnL {
    pub realized: f64,
    pub unrealized: f64,
    pub total: f64,
}

fn default_trade_status() -> String {
    "open".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeRecord {
    pub id: i64,
    pub symbol: String,
    pub right: String,
    pub strike: f64,
    pub expiry: String,
    pub side: String,
    pub quantity: i32,
    pub entry_price: f64,
    pub exit_price: Option<f64>,
    pub pnl: Option<f64>,
    #[serde(default = "default_trade_status")]
    pub status: String,
    pub timestamp: String,
    #[serde(default)]
    pub underlying_atr: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradingStatus {
    Idle,
    Starting,
    Running,
    Stopping,
    Error(String),
}

impl Default for TradingStatus {
    fn default() -> Self {
        TradingStatus::Idle
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingState {
    pub status: TradingStatus,
    pub positions: Vec<Position>,
    pub daily_pnl: DailyPnL,
    pub trades_today: Vec<TradeRecord>,
    pub total_trades: i32,
    pub winning_trades: i32,
    pub losing_trades: i32,
    pub last_signal: Option<String>,
    pub last_signal_time: Option<String>,
    /// Last IBKR account summary (NetLiquidation, BuyingPower, etc.); tag -> value.
    pub account_metrics: Option<serde_json::Value>,
    /// Signal DataFrame: list of {symbol, date, open, high, low, close, volume, signal} per candle.
    pub signal_data: Option<serde_json::Value>,
}

impl Default for TradingState {
    fn default() -> Self {
        Self {
            status: TradingStatus::Idle,
            positions: Vec::new(),
            daily_pnl: DailyPnL {
                realized: 0.0,
                unrealized: 0.0,
                total: 0.0,
            },
            trades_today: Vec::new(),
            total_trades: 0,
            winning_trades: 0,
            losing_trades: 0,
            last_signal: None,
            last_signal_time: None,
            account_metrics: None,
            signal_data: None,
        }
    }
}
