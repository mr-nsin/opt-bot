use serde::{Deserialize, Deserializer, Serialize};

fn deserialize_quantity_loose<'de, D>(deserializer: D) -> Result<i32, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Qty {
        I32(i32),
        I64(i64),
        F64(f64),
        String(String),
    }
    match Qty::deserialize(deserializer)? {
        Qty::I32(i) => Ok(i),
        Qty::I64(i) => i
            .try_into()
            .map_err(|_| serde::de::Error::custom("quantity out of i32 range")),
        Qty::F64(f) => Ok(f.round() as i32),
        Qty::String(s) => s
            .parse::<i32>()
            .map_err(|_| serde::de::Error::custom("invalid quantity string")),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub strike: f64,
    pub right: String,
    pub expiry: String,
    #[serde(default, deserialize_with = "deserialize_quantity_loose")]
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

#[cfg(test)]
mod position_deserialize_tests {
    use super::*;

    #[test]
    fn quantity_accepts_f64_from_sidecar_json() {
        let j = serde_json::json!({
            "symbol": "TSLA",
            "strike": 350.0,
            "right": "C",
            "expiry": "20260313",
            "quantity": 2.0,
            "avg_price": 1.5,
            "current_price": 1.55,
            "pnl": 10.0,
            "pnl_percent": 3.33
        });
        let p: Position = serde_json::from_value(j).unwrap();
        assert_eq!(p.quantity, 2);
    }
}
