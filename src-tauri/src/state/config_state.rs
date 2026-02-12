use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockConfig {
    pub amount: f64,
}

/// Trading configuration with serde aliases to support both the legacy
/// config.json field names (camelCase / UPPER_CASE) and the new snake_case names.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct TradingConfig {
    pub profit_increment: f64,
    #[serde(alias = "expiryToTrade")]
    pub expiry_to_trade: String,
    #[serde(alias = "SPY_QQQ_EXPIRY")]
    pub spy_qqq_expiry: String,
    #[serde(alias = "USE_DIFF_EXPIRY_INDEX")]
    pub use_diff_expiry_index: String,
    #[serde(alias = "IP")]
    pub ip: String,
    #[serde(alias = "PORT")]
    pub port: u16,
    #[serde(alias = "CLIENTID")]
    pub client_id: i32,
    #[serde(alias = "ACCOUNT_ID")]
    pub account_id: String,
    #[serde(alias = "marketStartTime")]
    pub market_start_time: String,
    #[serde(alias = "scriptStartTime")]
    pub script_start_time: String,
    #[serde(alias = "scriptEndTime")]
    pub script_end_time: String,
    #[serde(alias = "VWAP_ON_OFF")]
    pub vwap_on_off: String,
    #[serde(alias = "ORDER_TRANSMIT")]
    pub order_transmit: bool,
    #[serde(alias = "USE_TIMER_IN_ORDER")]
    pub use_timer_in_order: String,
    #[serde(alias = "ORDER_EXPIRY_TIMER")]
    pub order_expiry_timer: i32,
    #[serde(alias = "CALL_DELTA_CHECK")]
    pub call_delta_check: f64,
    #[serde(alias = "PUT_DELTA_CHECK")]
    pub put_delta_check: f64,
    #[serde(alias = "VOLUME_CHECK")]
    pub volume_check: i32,
    #[serde(alias = "ATR_CHECKS")]
    pub atr_checks: f64,
    #[serde(alias = "ACTIVE_VOLUME")]
    pub active_volume: i32,
    #[serde(alias = "MAX_CONTRACT_AMOUNT")]
    pub max_contract_amount: f64,
    #[serde(alias = "ATR_VALUE")]
    pub atr_value: f64,
    #[serde(alias = "SHARE_VOLUME")]
    pub share_volume: i32,
    #[serde(alias = "BODY")]
    pub body: f64,
    #[serde(alias = "MIDPOINT_OFFSET")]
    pub midpoint_offset: f64,
    #[serde(alias = "QUANTITY")]
    pub quantity: i32,
    #[serde(alias = "fetchValue")]
    pub fetch_value: String,
    #[serde(alias = "candleTime")]
    pub candle_time: String,
    pub distance_between_trade: i32,
    #[serde(alias = "AVG_VOLUMNS_CANDLES")]
    pub avg_volumes_candles: i32,
    #[serde(alias = "stockData")]
    pub stock_data: HashMap<String, StockConfig>,
    #[serde(alias = "stockListToTrade")]
    pub stock_list_to_trade: HashMap<String, String>,
    #[serde(alias = "perDayTrades")]
    pub per_day_trades: i32,
    pub loss_amount_day: f64,
    pub profit_amount_day: f64,
}

impl Default for TradingConfig {
    fn default() -> Self {
        let mut stock_data = HashMap::new();
        stock_data.insert("SPY".into(), StockConfig { amount: 350.0 });
        stock_data.insert("QQQ".into(), StockConfig { amount: 350.0 });

        let mut stock_list = HashMap::new();
        stock_list.insert("SPY".into(), "NASDAQ".into());
        stock_list.insert("QQQ".into(), "NASDAQ".into());

        Self {
            profit_increment: 0.03,
            expiry_to_trade: "next".into(),
            spy_qqq_expiry: "0DTE".into(),
            use_diff_expiry_index: "yes".into(),
            ip: "127.0.0.1".into(),
            port: 7497,
            client_id: 0,
            account_id: String::new(),
            market_start_time: "19:00:00".into(),
            script_start_time: "0935".into(),
            script_end_time: "1545".into(),
            vwap_on_off: "ON".into(),
            order_transmit: true,
            use_timer_in_order: "ON".into(),
            order_expiry_timer: 15,
            call_delta_check: 0.35,
            put_delta_check: -0.35,
            volume_check: 100,
            atr_checks: 0.047,
            active_volume: 5,
            max_contract_amount: 350.0,
            atr_value: 0.99,
            share_volume: 1,
            body: 2.0,
            midpoint_offset: 0.01,
            quantity: 2,
            fetch_value: "1 D".into(),
            candle_time: "5 mins".into(),
            distance_between_trade: 610,
            avg_volumes_candles: 30,
            stock_data,
            stock_list_to_trade: stock_list,
            per_day_trades: 3,
            loss_amount_day: 200.0,
            profit_amount_day: 200.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AppSettings {
    pub theme: String,
    pub trading_mode: String,
    pub font_size: i32,
    pub show_notifications: bool,
    pub auto_start_trading: bool,
    pub log_level: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme: "dark".into(),
            trading_mode: "demo".into(),
            font_size: 14,
            show_notifications: true,
            auto_start_trading: false,
            log_level: "info".into(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigState {
    pub trading: TradingConfig,
    pub settings: AppSettings,
}

impl Default for ConfigState {
    fn default() -> Self {
        Self {
            trading: TradingConfig::default(),
            settings: AppSettings::default(),
        }
    }
}

// ==========================================
// File I/O helpers for config persistence
// ==========================================

impl ConfigState {
    /// Load TradingConfig from disk.
    /// Tries app data dir first, then falls back to legacy ./config.json
    pub fn load_trading_config() -> Option<TradingConfig> {
        // Try app data dir first
        let app_data = crate::utils::paths::app_data_dir();
        let primary = app_data.join("config.json");

        if primary.exists() {
            if let Ok(contents) = std::fs::read_to_string(&primary) {
                match serde_json::from_str::<TradingConfig>(&contents) {
                    Ok(config) => {
                        log::info!("Loaded config from {:?}", primary);
                        return Some(config);
                    }
                    Err(e) => log::warn!("Failed to parse config at {:?}: {}", primary, e),
                }
            }
        }

        // Fallback to legacy config.json in current directory
        if let Ok(contents) = std::fs::read_to_string("config.json") {
            match serde_json::from_str::<TradingConfig>(&contents) {
                Ok(config) => {
                    log::info!("Loaded config from legacy ./config.json");
                    return Some(config);
                }
                Err(e) => log::warn!("Failed to parse legacy config.json: {}", e),
            }
        }

        None
    }

    /// Save TradingConfig to app data directory
    pub fn save_trading_config(config: &TradingConfig) -> Result<(), String> {
        let app_data = crate::utils::paths::app_data_dir();
        if !app_data.exists() {
            std::fs::create_dir_all(&app_data).map_err(|e| format!("Create dir: {}", e))?;
        }
        let path = app_data.join("config.json");
        let json =
            serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {}", e))?;
        std::fs::write(&path, json).map_err(|e| format!("Write config: {}", e))?;
        log::info!("Config saved to {:?}", path);
        Ok(())
    }

    /// Load AppSettings from disk
    pub fn load_settings() -> Option<AppSettings> {
        let app_data = crate::utils::paths::app_data_dir();
        let path = app_data.join("settings.json");

        if path.exists() {
            if let Ok(contents) = std::fs::read_to_string(&path) {
                match serde_json::from_str::<AppSettings>(&contents) {
                    Ok(settings) => {
                        log::info!("Loaded settings from {:?}", path);
                        return Some(settings);
                    }
                    Err(e) => log::warn!("Failed to parse settings at {:?}: {}", path, e),
                }
            }
        }

        None
    }

    /// Save AppSettings to disk
    pub fn save_settings(settings: &AppSettings) -> Result<(), String> {
        let app_data = crate::utils::paths::app_data_dir();
        if !app_data.exists() {
            std::fs::create_dir_all(&app_data).map_err(|e| format!("Create dir: {}", e))?;
        }
        let path = app_data.join("settings.json");
        let json =
            serde_json::to_string_pretty(settings).map_err(|e| format!("Serialize: {}", e))?;
        std::fs::write(&path, json).map_err(|e| format!("Write settings: {}", e))?;
        log::info!("Settings saved to {:?}", path);
        Ok(())
    }
}
