use crate::sidecar::{manager, protocol::*};
use crate::state::app_state::AppState;
use crate::state::trading_state::TradingStatus;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub async fn start_trading(
    config: serde_json::Value,
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    let mut app = state.lock().await;

    // Check license
    if !app.licensed {
        return Err("Valid license required to start trading".into());
    }

    // Check if already running
    if matches!(app.trading.status, TradingStatus::Running) {
        return Err("Trading is already running".into());
    }

    app.trading.status = TradingStatus::Starting;
    drop(app);

    // Spawn sidecar if not running
    if !manager::is_running().await {
        if let Err(e) = manager::spawn_sidecar(&app_handle).await {
            let mut app = state.lock().await;
            app.trading.status = TradingStatus::Idle;
            return Err(e);
        }
    }

    // Send start command to sidecar
    let request = SidecarRequest::new(
        methods::START_TRADING,
        Some(serde_json::json!({ "config": config })),
    );

    if let Err(e) = manager::send_request(&request).await {
        let mut app = state.lock().await;
        app.trading.status = TradingStatus::Idle;
        return Err(e);
    }

    // Update state
    let mut app = state.lock().await;
    app.trading.status = TradingStatus::Running;
    app.sidecar_running = true;

    Ok("Trading started".into())
}

#[tauri::command]
pub async fn stop_trading(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    let mut app = state.lock().await;

    if !matches!(app.trading.status, TradingStatus::Running) {
        return Err("Trading is not running".into());
    }

    app.trading.status = TradingStatus::Stopping;
    drop(app);

    let request = SidecarRequest::new(methods::STOP_TRADING, None);
    if let Err(e) = manager::send_request(&request).await {
        let mut app = state.lock().await;
        app.trading.status = TradingStatus::Running;
        return Err(e);
    }

    let mut app = state.lock().await;
    app.trading.status = TradingStatus::Idle;

    Ok("Trading stopped".into())
}

#[tauri::command]
pub async fn emergency_stop(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    // Send emergency stop to sidecar
    let request = SidecarRequest::new(methods::EMERGENCY_STOP, None);
    let _ = manager::send_request(&request).await;

    // Force kill sidecar
    manager::kill_sidecar().await?;

    // Update state
    let mut app = state.lock().await;
    app.trading.status = TradingStatus::Idle;
    app.sidecar_running = false;

    Ok("Emergency stop executed".into())
}

#[tauri::command]
pub async fn get_trading_status(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    let app = state.lock().await;

    Ok(serde_json::json!({
        "status": app.trading.status,
        "sidecar_running": app.sidecar_running,
        "connected_to_tws": app.connected_to_tws,
        "daily_pnl": app.trading.daily_pnl,
        "total_trades": app.trading.total_trades,
        "winning_trades": app.trading.winning_trades,
        "losing_trades": app.trading.losing_trades,
    }))
}

#[tauri::command]
pub async fn simulate_demo(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    // Spawn sidecar if not running
    if !manager::is_running().await {
        manager::spawn_sidecar(&app_handle).await?;
        // Brief pause for sidecar to initialize
        tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
    }

    let request = SidecarRequest::new(methods::SIMULATE_DEMO, None);
    manager::send_request(&request).await?;

    let mut app = state.lock().await;
    app.sidecar_running = true;

    Ok("Demo simulation started".into())
}

#[tauri::command]
pub async fn get_account_metrics(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<Option<serde_json::Value>, String> {
    let app = state.lock().await;
    Ok(app.trading.account_metrics.clone())
}
