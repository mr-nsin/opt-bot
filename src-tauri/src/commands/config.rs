use crate::sidecar::{manager, protocol::methods};
use crate::sidecar::protocol::SidecarRequest;
use crate::state::app_state::AppState;
use crate::state::config_state::{AppSettings, ConfigState, TradingConfig};
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub async fn get_config(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    let app = state.lock().await;
    serde_json::to_value(&app.config.trading).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn save_config(
    config: TradingConfig,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    let mut app = state.lock().await;
    app.config.trading = config;

    // Persist to app data directory
    ConfigState::save_trading_config(&app.config.trading)?;

    // If the trading engine is running, push config so it picks up changes at runtime
    if manager::is_running().await {
        let config_value = serde_json::to_value(&app.config.trading).map_err(|e| e.to_string())?;
        let request = SidecarRequest::new(
            methods::UPDATE_CONFIG,
            Some(serde_json::json!({ "config": config_value })),
        );
        if let Err(e) = manager::send_request(&request).await {
            log::warn!("Could not push config to running engine: {}", e);
        }
    }

    Ok("Configuration saved".into())
}

#[tauri::command]
pub async fn get_settings(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    let app = state.lock().await;
    serde_json::to_value(&app.config.settings).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn save_settings(
    settings: AppSettings,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    let mut app = state.lock().await;
    app.config.settings = settings;

    // Persist settings to disk so they survive restarts
    ConfigState::save_settings(&app.config.settings)?;

    Ok("Settings saved".into())
}

/// Read config/settings.json from project if present (trading, strategy, databento, etc.) for UI display.
#[tauri::command]
pub async fn get_settings_file() -> Result<Option<serde_json::Value>, String> {
    Ok(ConfigState::read_settings_file_raw())
}
