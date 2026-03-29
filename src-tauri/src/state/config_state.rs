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
    pub emergency_close_buffer_seconds: i32,
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
    #[serde(alias = "ADX_ON_OFF", default)]
    pub adx_on_off: String,
    #[serde(alias = "ADX_THRESHOLD", default)]
    pub adx_threshold: f64,
    #[serde(alias = "RSI_DIVERGENCE_ON_OFF", default)]
    pub rsi_divergence_on_off: String,
    #[serde(alias = "VOLUME_DIVERGENCE_ON_OFF", default)]
    pub volume_divergence_on_off: String,
    #[serde(alias = "LIQUIDITY_SWAP_ON_OFF", default)]
    pub liquidity_swap_on_off: String,
    #[serde(alias = "LIQUIDITY_CHECK_ON_OFF", default)]
    pub liquidity_check_on_off: String,
    #[serde(alias = "LIQUIDITY_MIN_VOLUME", default)]
    pub liquidity_min_volume: i32,
    #[serde(alias = "LIQUIDITY_MAX_SPREAD_PCT", default)]
    pub liquidity_max_spread_pct: f64,
}

/// Default symbols aligned with config.json — all symbols from stockData/stockListToTrade.
const DEFAULT_SYMBOLS: &[(&str, &str)] = &[
    ("SPY", "NASDAQ"),
    ("QQQ", "NASDAQ"),
    ("TSLA", "NASDAQ"),
    ("AMZN", "NASDAQ"),
    ("AAPL", "NASDAQ"),
    ("AMD", "NASDAQ"),
    ("NVDA", "NASDAQ"),
    ("MSFT", "NASDAQ"),
    ("BABA", "NASDAQ"),
];

impl Default for TradingConfig {
    fn default() -> Self {
        let mut stock_data = HashMap::new();
        let mut stock_list = HashMap::new();
        for (sym, exch) in DEFAULT_SYMBOLS {
            stock_data.insert((*sym).into(), StockConfig { amount: 350.0 });
            stock_list.insert((*sym).into(), (*exch).into());
        }

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
            emergency_close_buffer_seconds: 5,
            avg_volumes_candles: 30,
            stock_data,
            stock_list_to_trade: stock_list,
            per_day_trades: 3,
            loss_amount_day: 200.0,
            profit_amount_day: 200.0,
            adx_on_off: "ON".into(),
            adx_threshold: 25.0,
            rsi_divergence_on_off: "ON".into(),
            volume_divergence_on_off: "ON".into(),
            liquidity_swap_on_off: "ON".into(),
            liquidity_check_on_off: "ON".into(),
            liquidity_min_volume: 20,
            liquidity_max_spread_pct: 15.0,
        }
    }
}

fn default_positions_update_interval_ms() -> i32 {
    250
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
    pub update_interval: i32,
    #[serde(default = "default_positions_update_interval_ms")]
    pub positions_update_interval_ms: i32,
    pub show_charts: bool,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme: "dark".into(),
            trading_mode: "demo".into(),
            font_size: 16,
            show_notifications: true,
            auto_start_trading: false,
            log_level: "info".into(),
            update_interval: 1000,
            positions_update_interval_ms: 250,
            show_charts: true,
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

/// Config.json embedded at compile time from project root.
/// Used as fallback when running as standalone exe (no resources folder).
/// Build from project root so this path resolves: src-tauri/src/state/ -> ../../../config.json
#[cfg(not(test))]
const EMBEDDED_CONFIG: &str = include_str!("../../../config.json");
#[cfg(test)]
const EMBEDDED_CONFIG: &str = "{}";

/// UI settings nested under "ui" key in config.json.
#[derive(serde::Deserialize)]
#[serde(default)]
struct ConfigUi {
    theme: String,
    trading_mode: String,
    font_size: i32,
    update_interval: i32,
    #[serde(default = "default_positions_update_interval_ms")]
    positions_update_interval_ms: i32,
    show_charts: bool,
    show_notifications: bool,
    auto_start_trading: bool,
    log_level: String,
}

impl Default for ConfigUi {
    fn default() -> Self {
        Self {
            theme: String::new(),
            trading_mode: String::new(),
            font_size: 0,
            update_interval: 0,
            positions_update_interval_ms: default_positions_update_interval_ms(),
            show_charts: false,
            show_notifications: false,
            auto_start_trading: false,
            log_level: String::new(),
        }
    }
}

/// Combined config.json structure: trading params + ui key (or flat fallback for migration).
#[derive(serde::Deserialize)]
struct ConfigFile {
    #[serde(default)]
    ui: Option<ConfigUi>,
    #[serde(default)]
    theme: Option<String>,
    #[serde(default)]
    trading_mode: Option<String>,
    #[serde(default)]
    font_size: Option<i32>,
    #[serde(default)]
    update_interval: Option<i32>,
    #[serde(default)]
    show_charts: Option<bool>,
    #[serde(default)]
    show_notifications: Option<bool>,
    #[serde(default)]
    auto_start_trading: Option<bool>,
    #[serde(default)]
    log_level: Option<String>,
    #[serde(flatten)]
    trading: TradingConfig,
}

impl ConfigState {
    /// Paths to try for project config.json (root config.json always prioritized; BOT.py source of truth)
    fn project_config_paths() -> Vec<std::path::PathBuf> {
        let mut paths = vec![std::path::PathBuf::from("config.json")];
        if let Ok(cwd) = std::env::current_dir() {
            paths.push(cwd.join("config.json"));
            paths.push(cwd.join("..").join("config.json"));
        }
        // When running as exe: config.json next to exe (user-placed) or in resources/ (bundled default)
        if let Ok(exe) = std::env::current_exe() {
            if let Some(exe_dir) = exe.parent() {
                paths.push(exe_dir.join("config.json"));
                paths.push(exe_dir.join("resources").join("config.json"));
            }
        }
        paths
    }

    /// Ensure at least one symbol; use all config.json defaults when empty.
    fn fix_trading_symbols(config: &mut TradingConfig) {
        if config.stock_list_to_trade.is_empty() {
            for (sym, exch) in DEFAULT_SYMBOLS {
                config.stock_list_to_trade.insert((*sym).into(), (*exch).into());
            }
            if config.stock_data.is_empty() {
                for (sym, _) in DEFAULT_SYMBOLS {
                    config.stock_data.insert((*sym).into(), StockConfig { amount: 350.0 });
                }
            }
            log::info!("Config had no symbols; defaulting to all symbols from config.json: {:?}", DEFAULT_SYMBOLS.iter().map(|(s, _)| *s).collect::<Vec<_>>());
        }
    }

    fn settings_from_config_file(f: &ConfigFile) -> AppSettings {
        let def = AppSettings::default();
        let theme = f
            .ui
            .as_ref()
            .map(|u| u.theme.as_str())
            .or(f.theme.as_deref())
            .filter(|s| !s.is_empty())
            .unwrap_or(def.theme.as_str());
        let trading_mode = f
            .ui
            .as_ref()
            .map(|u| u.trading_mode.as_str())
            .or(f.trading_mode.as_deref())
            .filter(|s| !s.is_empty())
            .unwrap_or(def.trading_mode.as_str());
        let font_size = f.ui.as_ref().map(|u| u.font_size).or(f.font_size).unwrap_or(def.font_size).clamp(12, 24);
        let update_interval = f.ui.as_ref().map(|u| u.update_interval).or(f.update_interval).unwrap_or(def.update_interval);
        let positions_update_interval_ms = f
            .ui
            .as_ref()
            .map(|u| u.positions_update_interval_ms)
            .unwrap_or(def.positions_update_interval_ms)
            .clamp(50, 5000);
        let show_charts = f.ui.as_ref().map(|u| u.show_charts).or(f.show_charts).unwrap_or(def.show_charts);
        let show_notifications = f.ui.as_ref().map(|u| u.show_notifications).or(f.show_notifications).unwrap_or(def.show_notifications);
        let auto_start_trading = f.ui.as_ref().map(|u| u.auto_start_trading).or(f.auto_start_trading).unwrap_or(def.auto_start_trading);
        let log_level = f
            .ui
            .as_ref()
            .map(|u| u.log_level.as_str())
            .or(f.log_level.as_deref())
            .filter(|s| !s.is_empty())
            .unwrap_or(def.log_level.as_str());
        AppSettings {
            theme: theme.to_string(),
            trading_mode: trading_mode.to_string(),
            font_size,
            update_interval,
            positions_update_interval_ms,
            show_charts,
            show_notifications,
            auto_start_trading,
            log_level: log_level.to_string(),
        }
    }

    /// Load full ConfigState (trading + settings) from config.json. Single source only.
    /// Pass `resource_config_path` from `app.path().resource_dir().map(|d| d.join("config.json"))` for packaged bundles.
    ///
    /// Order: project paths, app data (UI saves), bundled resource, legacy `./config.json`, embedded.
    pub fn load_config_with_resource_path(
        resource_config_path: Option<std::path::PathBuf>,
    ) -> Option<ConfigState> {
        let try_load = |contents: &str| -> Option<ConfigState> {
            let file: ConfigFile = serde_json::from_str(contents).ok()?;
            let settings = Self::settings_from_config_file(&file);
            let mut trading = file.trading;
            Self::fix_trading_symbols(&mut trading);
            Some(ConfigState { trading, settings })
        };

        // 1) Project config.json
        for path in Self::project_config_paths() {
            if !path.exists() {
                continue;
            }
            let path = path.canonicalize().unwrap_or(path);
            if let Ok(contents) = std::fs::read_to_string(&path) {
                if let Some(state) = try_load(&contents) {
                    log::info!("Loaded config from {:?} ({} symbols)", path, state.trading.stock_list_to_trade.len());
                    return Some(state);
                }
            }
        }

        // 2) App data dir
        let app_data = crate::utils::paths::app_data_dir();
        let primary = app_data.join("config.json");
        if primary.exists() {
            if let Ok(contents) = std::fs::read_to_string(&primary) {
                if let Some(state) = try_load(&contents) {
                    log::info!("Loaded config from app data {:?} ({} symbols)", primary, state.trading.stock_list_to_trade.len());
                    return Some(state);
                }
            }
        }

        // 3) Bundled resource path
        if let Some(ref path) = resource_config_path {
            if path.exists() {
                if let Ok(contents) = std::fs::read_to_string(path) {
                    if let Some(state) = try_load(&contents) {
                        log::info!("Loaded config from bundled resource {:?} ({} symbols)", path, state.trading.stock_list_to_trade.len());
                        return Some(state);
                    }
                }
            }
        }

        // 4) Legacy ./config.json
        if let Ok(contents) = std::fs::read_to_string("config.json") {
            if let Some(state) = try_load(&contents) {
                log::info!("Loaded config from legacy ./config.json ({} symbols)", state.trading.stock_list_to_trade.len());
                return Some(state);
            }
        }

        // 5) Embedded config (standalone exe — no resources folder needed)
        if let Some(state) = try_load(EMBEDDED_CONFIG) {
            log::info!("Loaded config from embedded binary ({} symbols) — standalone exe, no resources folder", state.trading.stock_list_to_trade.len());
            return Some(state);
        }

        None
    }

    /// Load config (convenience; no resource path - use load_config_with_resource_path for exe).
    pub fn load_config() -> Option<ConfigState> {
        Self::load_config_with_resource_path(None)
    }

    /// Legacy: Load only TradingConfig (for compatibility). Prefer load_config().
    pub fn load_trading_config() -> Option<TradingConfig> {
        Self::load_config().map(|c| c.trading)
    }

    /// Save full ConfigState (trading + settings) to config.json. Single source.
    pub fn save_full_config(config: &ConfigState) -> Result<(), String> {
        let app_data = crate::utils::paths::app_data_dir();
        if !app_data.exists() {
            std::fs::create_dir_all(&app_data).map_err(|e| format!("Create dir: {}", e))?;
        }
        let path = app_data.join("config.json");
        let json = Self::config_to_json(config)?;
        std::fs::write(&path, &json).map_err(|e| format!("Write config: {}", e))?;
        log::info!("Config saved to {:?}", path);

        Self::save_config_to_project(config);
        Ok(())
    }

    /// Build JSON for config.json (trading + ui nested)
    fn config_to_json(config: &ConfigState) -> Result<String, String> {
        use serde_json::{Map, Value};
        let stock_data_map: Map<String, Value> = config
            .trading
            .stock_data
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!({ "amount": v.amount })))
            .collect();
        let stock_list_map: Map<String, Value> = config
            .trading
            .stock_list_to_trade
            .iter()
            .map(|(k, v)| (k.clone(), Value::String(v.clone())))
            .collect();
        let t = &config.trading;
        let s = &config.settings;
        let mut ui_map = Map::new();
        ui_map.insert("theme".into(), Value::String(s.theme.clone()));
        ui_map.insert("trading_mode".into(), Value::String(s.trading_mode.clone()));
        ui_map.insert("font_size".into(), Value::Number(s.font_size.into()));
        ui_map.insert("update_interval".into(), Value::Number(s.update_interval.into()));
        ui_map.insert(
            "positions_update_interval_ms".into(),
            Value::Number(s.positions_update_interval_ms.into()),
        );
        ui_map.insert("show_charts".into(), Value::Bool(s.show_charts));
        ui_map.insert("show_notifications".into(), Value::Bool(s.show_notifications));
        ui_map.insert("auto_start_trading".into(), Value::Bool(s.auto_start_trading));
        ui_map.insert("log_level".into(), Value::String(s.log_level.clone()));
        let mut m = Map::new();
        m.insert("ui".into(), Value::Object(ui_map));
        m.insert("profit_increment".into(), Value::Number(serde_json::Number::from_f64(t.profit_increment).unwrap_or(0.into())));
        m.insert("expiryToTrade".into(), Value::String(t.expiry_to_trade.clone()));
        m.insert("SPY_QQQ_EXPIRY".into(), Value::String(t.spy_qqq_expiry.clone()));
        m.insert("USE_DIFF_EXPIRY_INDEX".into(), Value::String(t.use_diff_expiry_index.clone()));
        m.insert("IP".into(), Value::String(t.ip.clone()));
        m.insert("PORT".into(), Value::Number(t.port.into()));
        m.insert("CLIENTID".into(), Value::Number(t.client_id.into()));
        m.insert("ACCOUNT_ID".into(), Value::String(t.account_id.clone()));
        m.insert("marketStartTime".into(), Value::String(t.market_start_time.clone()));
        m.insert("scriptStartTime".into(), Value::String(t.script_start_time.clone()));
        m.insert("scriptEndTime".into(), Value::String(t.script_end_time.clone()));
        let mut mh = Map::new();
        mh.insert("start".into(), Value::String(t.script_start_time.clone()));
        mh.insert("end".into(), Value::String(t.script_end_time.clone()));
        m.insert("market_hours".into(), Value::Object(mh));
        m.insert("VWAP_ON_OFF".into(), Value::String(t.vwap_on_off.clone()));
        m.insert("ORDER_TRANSMIT".into(), Value::Bool(t.order_transmit));
        m.insert("USE_TIMER_IN_ORDER".into(), Value::String(t.use_timer_in_order.clone()));
        m.insert("ORDER_EXPIRY_TIMER".into(), Value::Number(t.order_expiry_timer.into()));
        m.insert("CALL_DELTA_CHECK".into(), Value::Number(serde_json::Number::from_f64(t.call_delta_check).unwrap_or(0.into())));
        m.insert("PUT_DELTA_CHECK".into(), Value::Number(serde_json::Number::from_f64(t.put_delta_check).unwrap_or(0.into())));
        m.insert("VOLUME_CHECK".into(), Value::Number(t.volume_check.into()));
        m.insert("ATR_CHECKS".into(), Value::Number(serde_json::Number::from_f64(t.atr_checks).unwrap_or(0.into())));
        m.insert("ACTIVE_VOLUME".into(), Value::Number(t.active_volume.into()));
        m.insert("MAX_CONTRACT_AMOUNT".into(), Value::Number(serde_json::Number::from_f64(t.max_contract_amount).unwrap_or(0.into())));
        m.insert("ATR_VALUE".into(), Value::Number(serde_json::Number::from_f64(t.atr_value).unwrap_or(0.into())));
        m.insert("SHARE_VOLUME".into(), Value::Number(t.share_volume.into()));
        m.insert("BODY".into(), Value::Number(serde_json::Number::from_f64(t.body).unwrap_or(0.into())));
        m.insert("MIDPOINT_OFFSET".into(), Value::Number(serde_json::Number::from_f64(t.midpoint_offset).unwrap_or(0.into())));
        m.insert("QUANTITY".into(), Value::Number(t.quantity.into()));
        m.insert("fetchValue".into(), Value::String(t.fetch_value.clone()));
        m.insert("candleTime".into(), Value::String(t.candle_time.clone()));
        m.insert("distance_between_trade".into(), Value::Number(t.distance_between_trade.into()));
        m.insert("emergency_close_buffer_seconds".into(), Value::Number(t.emergency_close_buffer_seconds.into()));
        m.insert("AVG_VOLUMNS_CANDLES".into(), Value::Number(t.avg_volumes_candles.into()));
        m.insert("stockData".into(), Value::Object(stock_data_map));
        m.insert("stockListToTrade".into(), Value::Object(stock_list_map));
        m.insert("perDayTrades".into(), Value::Number(t.per_day_trades.into()));
        m.insert("loss_amount_day".into(), Value::Number(serde_json::Number::from_f64(t.loss_amount_day).unwrap_or(0.into())));
        m.insert("profit_amount_day".into(), Value::Number(serde_json::Number::from_f64(t.profit_amount_day).unwrap_or(0.into())));
        m.insert("ADX_ON_OFF".into(), Value::String(t.adx_on_off.clone()));
        m.insert("ADX_THRESHOLD".into(), Value::Number(serde_json::Number::from_f64(t.adx_threshold).unwrap_or(0.into())));
        m.insert("RSI_DIVERGENCE_ON_OFF".into(), Value::String(t.rsi_divergence_on_off.clone()));
        m.insert("VOLUME_DIVERGENCE_ON_OFF".into(), Value::String(t.volume_divergence_on_off.clone()));
        m.insert("LIQUIDITY_SWAP_ON_OFF".into(), Value::String(t.liquidity_swap_on_off.clone()));
        m.insert("LIQUIDITY_CHECK_ON_OFF".into(), Value::String(t.liquidity_check_on_off.clone()));
        m.insert("LIQUIDITY_MIN_VOLUME".into(), Value::Number(t.liquidity_min_volume.into()));
        m.insert("LIQUIDITY_MAX_SPREAD_PCT".into(), Value::Number(serde_json::Number::from_f64(t.liquidity_max_spread_pct).unwrap_or(0.into())));
        serde_json::to_string_pretty(&Value::Object(m)).map_err(|e| format!("Serialize: {}", e))
    }

    /// Save full config to project config.json. Kept for backwards compatibility.
    pub fn save_trading_config(config: &TradingConfig) -> Result<(), String> {
        let state = ConfigState {
            trading: config.clone(),
            settings: AppSettings::default(),
        };
        Self::save_full_config(&state)
    }

    /// Write config to project config.json (trading + settings)
    fn save_config_to_project(config: &ConfigState) {
        let json = match Self::config_to_json(config) {
            Ok(j) => j,
            Err(e) => {
                log::warn!("Serialize project config: {}", e);
                return;
            }
        };
        for path in Self::project_config_paths() {
            if path.exists() {
                if std::fs::write(&path, &json).is_ok() {
                    log::info!("Config saved to project {:?}", path);
                    return;
                }
            }
        }
        if let Ok(cwd) = std::env::current_dir() {
            let path = cwd.join("config.json");
            if std::fs::write(&path, &json).is_ok() {
                log::info!("Config saved to project {:?}", path);
            }
        }
    }

    /// Read config.json (single source); returns raw JSON for UI display.
    pub fn read_config_raw() -> Option<serde_json::Value> {
        let contents = Self::read_config_contents()?;
        serde_json::from_str::<serde_json::Value>(&contents).ok()
    }

    fn read_config_contents() -> Option<String> {
        for path in Self::project_config_paths() {
            if path.exists() {
                if let Ok(c) = std::fs::read_to_string(&path) {
                    return Some(c);
                }
            }
        }
        let app_data = crate::utils::paths::app_data_dir();
        let primary = app_data.join("config.json");
        if primary.exists() {
            if let Ok(c) = std::fs::read_to_string(&primary) {
                return Some(c);
            }
        }
        None
    }
}
