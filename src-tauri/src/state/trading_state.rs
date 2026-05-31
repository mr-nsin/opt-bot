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
    pub stoploss_price: Option<f64>,
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
    /// ISO time when the position was opened (from entry fill / bot order).
    #[serde(default)]
    pub entry_time: Option<String>,
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
    /// Whether the first pnl_update has been forwarded to the UI (ensures initial value always reaches frontend).
    #[serde(skip, default)]
    pub pnl_initialized: bool,
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
            pnl_initialized: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Position;

    /// Demo / engine emit_position shape must deserialize for Rust AppState + IPC.
    #[test]
    fn position_deserializes_from_engine_emit_shape() {
        let json = r#"{
            "symbol": "AAPL",
            "strike": 230.0,
            "right": "C",
            "expiry": "20260418",
            "quantity": 2,
            "qty": 2,
            "avg_price": 3.85,
            "current_price": 3.90,
            "bid": 3.88,
            "ask": 3.92,
            "last": 3.90,
            "pnl": 10.0,
            "pnl_percent": 1.3,
            "profit_price": 5.0,
            "stoploss_price": 2.5,
            "exit_price_used": 3.88,
            "exit_price_source": "bid",
            "entry_time": "2026-04-04T14:30:00"
        }"#;
        let p: Position = serde_json::from_str(json).expect("demo position_update");
        assert_eq!(p.symbol, "AAPL");
        assert_eq!(p.last, Some(3.90));
        assert_eq!(p.bid, Some(3.88));
        assert_eq!(
            p.entry_time.as_deref(),
            Some("2026-04-04T14:30:00")
        );
    }
}
