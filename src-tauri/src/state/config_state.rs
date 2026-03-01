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
        stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
        stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });

        let mut stock_list = HashMap::new();
        stock_list.insert("MNQU5".into(), "CME".into());
        stock_list.insert("NQU5".into(), "CME".into());

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
    pub update_interval: i32,
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

impl ConfigState {
    /// Paths to try for project config.json (BOT.py source of truth)
    fn project_config_paths() -> Vec<std::path::PathBuf> {
        let mut paths = vec![std::path::PathBuf::from("config.json")];
        if let Ok(cwd) = std::env::current_dir() {
            paths.push(cwd.join("config.json"));
            paths.push(cwd.join("..").join("config.json"));
        }
        paths
    }

    /// Load TradingConfig from disk. Tries project config.json first (BOT.py source of truth), then app data, then legacy.
    pub fn load_trading_config() -> Option<TradingConfig> {
        // 1) Try project config.json first so Tauri trades what BOT.py uses
        for path in Self::project_config_paths() {
            if !path.exists() {
                continue;
            }
            let path = path.canonicalize().unwrap_or(path);
            if let Ok(contents) = std::fs::read_to_string(&path) {
                match serde_json::from_str::<TradingConfig>(&contents) {
                    Ok(mut config) => {
                        if config.stock_list_to_trade.is_empty() {
                            config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                            config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                            if config.stock_data.is_empty() {
                                config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                                config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                            }
                            log::info!("Config had no symbols; defaulting to MNQU5, NQU5");
                        } else {
                            // Only add missing NQU5/MNQU5 when list already has futures (MNQU5 or NQU5)
                            let has_mnq = config.stock_list_to_trade.contains_key("MNQU5");
                            let has_nq = config.stock_list_to_trade.contains_key("NQU5");
                            if has_mnq && !has_nq {
                                config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                                config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                            }
                            if has_nq && !has_mnq {
                                config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                                config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                            }
                        }
                        log::info!("Loaded config from project {:?} ({} symbols)", path, config.stock_list_to_trade.len());
                        return Some(config);
                    }
                    Err(e) => log::warn!("Failed to parse project config at {:?}: {}", path, e),
                }
            }
        }

        // 2) App data dir
        let app_data = crate::utils::paths::app_data_dir();
        let primary = app_data.join("config.json");
        if primary.exists() {
            if let Ok(contents) = std::fs::read_to_string(&primary) {
                if let Ok(mut config) = serde_json::from_str::<TradingConfig>(&contents) {
                    if config.stock_list_to_trade.is_empty() {
                        config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                        config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                        if config.stock_data.is_empty() {
                            config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                            config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                        }
                    } else {
                        let has_mnq = config.stock_list_to_trade.contains_key("MNQU5");
                        let has_nq = config.stock_list_to_trade.contains_key("NQU5");
                        if has_mnq && !has_nq {
                            config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                            config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                        }
                        if has_nq && !has_mnq {
                            config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                            config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                        }
                    }
                    log::info!("Loaded config from app data {:?} ({} symbols)", primary, config.stock_list_to_trade.len());
                    return Some(config);
                }
            }
        }

        // 3) Legacy ./config.json
        if let Ok(contents) = std::fs::read_to_string("config.json") {
            if let Ok(mut config) = serde_json::from_str::<TradingConfig>(&contents) {
                if config.stock_list_to_trade.is_empty() {
                    config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                    config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                    if config.stock_data.is_empty() {
                        config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                        config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                    }
                } else {
                    let has_mnq = config.stock_list_to_trade.contains_key("MNQU5");
                    let has_nq = config.stock_list_to_trade.contains_key("NQU5");
                    if has_mnq && !has_nq {
                        config.stock_list_to_trade.insert("NQU5".into(), "CME".into());
                        config.stock_data.insert("NQU5".into(), StockConfig { amount: 350.0 });
                    }
                    if has_nq && !has_mnq {
                        config.stock_list_to_trade.insert("MNQU5".into(), "CME".into());
                        config.stock_data.insert("MNQU5".into(), StockConfig { amount: 350.0 });
                    }
                }
                log::info!("Loaded config from legacy ./config.json ({} symbols)", config.stock_list_to_trade.len());
                return Some(config);
            }
        }

        None
    }

    /// Try to load config/settings.json (project-style) and merge into trading config and app settings.
    /// Paths tried: ./config/settings.json, then app_data_dir/../config/settings.json.
    /// Merges: trading.symbols -> stock_list_to_trade (CME), broker -> ip/port/client_id,
    /// trading.daily_profit_limit/loss -> profit_amount_day/loss_amount_day, ui -> settings.
    pub fn try_merge_settings_file(config: &mut ConfigState) {
        #[derive(serde::Deserialize)]
        struct SettingsFile {
            #[serde(default)]
            trading: SettingsTrading,
            #[serde(default)]
            broker: SettingsBroker,
            #[serde(default)]
            ui: SettingsUi,
        }
        #[derive(serde::Deserialize, Default)]
        struct SettingsTrading {
            #[serde(default)]
            symbols: Vec<String>,
            #[serde(default)]
            daily_profit_limit: Option<f64>,
            #[serde(default)]
            daily_loss_limit: Option<f64>,
            #[serde(default)]
            mode: String,
        }
        #[derive(serde::Deserialize, Default)]
        struct SettingsBroker {
            #[serde(default)]
            host: String,
            #[serde(default)]
            port: Option<u16>,
            #[serde(default)]
            client_id: Option<i32>,
        }
        #[derive(serde::Deserialize, Default)]
        struct SettingsUi {
            #[serde(default)]
            theme: String,
            #[serde(default)]
            font_size: Option<i32>,
            #[serde(default)]
            update_interval: Option<i32>,
            #[serde(default)]
            show_charts: Option<bool>,
        }

        // Try multiple paths so config/settings.json is found (dev: cwd may be project root or src-tauri)
        let mut paths: Vec<std::path::PathBuf> = Vec::new();
        paths.push(std::path::PathBuf::from("config").join("settings.json"));
        if let Ok(cwd) = std::env::current_dir() {
            paths.push(cwd.join("config").join("settings.json"));
            paths.push(cwd.join("..").join("config").join("settings.json"));
        }
        paths.push(
            crate::utils::paths::app_data_dir()
                .parent()
                .map(|p| p.join("config").join("settings.json"))
                .unwrap_or_else(|| std::path::PathBuf::from("config").join("settings.json")),
        );
        for path in &paths {
            if !path.exists() {
                continue;
            }
            let path = path.canonicalize().unwrap_or_else(|_| path.clone());
            let path_for_log = path.clone();
            let contents = match std::fs::read_to_string(&path) {
                Ok(c) => c,
                Err(_) => continue,
            };
            let file: SettingsFile = match serde_json::from_str(&contents) {
                Ok(f) => f,
                Err(e) => {
                    log::warn!("Failed to parse config/settings.json at {:?}: {}", path_for_log, e);
                    continue;
                }
            };
            log::info!("Merging config from {:?}", path_for_log);
            let c = &mut config.trading;
            let s = &mut config.settings;
            // Only overwrite symbols from settings.json when config has none (project config.json wins)
            if !file.trading.symbols.is_empty() && c.stock_list_to_trade.is_empty() {
                for sym in &file.trading.symbols {
                    c.stock_list_to_trade.insert(sym.clone(), "CME".into());
                }
                for sym in c.stock_list_to_trade.keys().cloned().collect::<Vec<_>>() {
                    c.stock_data.entry(sym).or_insert(StockConfig { amount: 350.0 });
                }
            }
            if let Some(v) = file.trading.daily_profit_limit {
                c.profit_amount_day = v;
            }
            if let Some(v) = file.trading.daily_loss_limit {
                c.loss_amount_day = v;
            }
            if !file.broker.host.is_empty() {
                c.ip = file.broker.host.clone();
            }
            if let Some(p) = file.broker.port {
                c.port = p;
            }
            if let Some(id) = file.broker.client_id {
                c.client_id = id;
            }
            if !file.ui.theme.is_empty() {
                s.theme = file.ui.theme.clone();
            }
            if let Some(fs) = file.ui.font_size {
                // Clamp to readable range so config/settings.json font_size=9 doesn't make UI tiny
                s.font_size = fs.clamp(12, 24);
            }
            if let Some(ui) = file.ui.update_interval {
                s.update_interval = ui;
            }
            if let Some(sc) = file.ui.show_charts {
                s.show_charts = sc;
            }
            if !file.trading.mode.is_empty() {
                s.trading_mode = file.trading.mode.clone();
            }
            return;
        }
    }

    /// Save TradingConfig to app data directory (and to project config.json in BOT.py format when writable)
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

        // Also write to project config.json so BOT.py and UI stay in sync (BOT.py key names)
        Self::save_trading_config_to_project(config);
        Ok(())
    }

    /// Write config to project config.json using BOT.py key names (IP, PORT, stockListToTrade, etc.)
    fn save_trading_config_to_project(config: &TradingConfig) {
        use serde_json::Value;
        let stock_data_map: std::collections::BTreeMap<String, Value> = config
            .stock_data
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!({ "amount": v.amount })))
            .collect();
        let stock_list_map: std::collections::BTreeMap<String, Value> = config
            .stock_list_to_trade
            .iter()
            .map(|(k, v)| (k.clone(), Value::String(v.clone())))
            .collect();
        let bot_json = serde_json::json!({
            "profit_increment": config.profit_increment,
            "expiryToTrade": config.expiry_to_trade,
            "SPY_QQQ_EXPIRY": config.spy_qqq_expiry,
            "USE_DIFF_EXPIRY_INDEX": config.use_diff_expiry_index,
            "IP": config.ip,
            "PORT": config.port,
            "CLIENTID": config.client_id,
            "ACCOUNT_ID": config.account_id,
            "marketStartTime": config.market_start_time,
            "scriptStartTime": config.script_start_time,
            "scriptEndTime": config.script_end_time,
            "VWAP_ON_OFF": config.vwap_on_off,
            "ORDER_TRANSMIT": config.order_transmit,
            "USE_TIMER_IN_ORDER": config.use_timer_in_order,
            "ORDER_EXPIRY_TIMER": config.order_expiry_timer,
            "CALL_DELTA_CHECK": config.call_delta_check,
            "PUT_DELTA_CHECK": config.put_delta_check,
            "VOLUME_CHECK": config.volume_check,
            "ATR_CHECKS": config.atr_checks,
            "ACTIVE_VOLUME": config.active_volume,
            "MAX_CONTRACT_AMOUNT": config.max_contract_amount,
            "ATR_VALUE": config.atr_value,
            "SHARE_VOLUME": config.share_volume,
            "BODY": config.body,
            "MIDPOINT_OFFSET": config.midpoint_offset,
            "QUANTITY": config.quantity,
            "fetchValue": config.fetch_value,
            "candleTime": config.candle_time,
            "distance_between_trade": config.distance_between_trade,
            "AVG_VOLUMNS_CANDLES": config.avg_volumes_candles,
            "stockData": stock_data_map,
            "stockListToTrade": stock_list_map,
            "perDayTrades": config.per_day_trades,
            "loss_amount_day": config.loss_amount_day,
            "profit_amount_day": config.profit_amount_day,
        });
        let json = match serde_json::to_string_pretty(&bot_json) {
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

    /// Read config/settings.json (project-style) if present; returns raw JSON for UI display.
    pub fn read_settings_file_raw() -> Option<serde_json::Value> {
        let mut paths: Vec<std::path::PathBuf> = vec![
            std::path::PathBuf::from("config").join("settings.json"),
        ];
        if let Ok(cwd) = std::env::current_dir() {
            paths.push(cwd.join("config").join("settings.json"));
            paths.push(cwd.join("..").join("config").join("settings.json"));
        }
        for path in &paths {
            if !path.exists() {
                continue;
            }
            if let Ok(contents) = std::fs::read_to_string(path) {
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(&contents) {
                    return Some(v);
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
