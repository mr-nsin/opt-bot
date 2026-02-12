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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyPnL {
    pub realized: f64,
    pub unrealized: f64,
    pub total: f64,
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
        }
    }
}
