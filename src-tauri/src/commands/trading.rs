use crate::sidecar::{manager, protocol::*};
use crate::state::app_state::AppState;
use crate::state::trading_state::TradingStatus;
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
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
    app_handle: AppHandle,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    let mut app = state.lock().await;

    if !matches!(app.trading.status, TradingStatus::Running) {
        return Err("Trading is not running".into());
    }

    app.trading.status = TradingStatus::Stopping;
    drop(app);

    // Tell the engine to stop gracefully (cancel orders, close positions, disconnect TWS)
    let request = SidecarRequest::new(methods::STOP_TRADING, None);
    let _ = manager::send_request(&request).await;

    // Give the engine time to cancel orders / close positions / disconnect TWS
    tokio::time::sleep(std::time::Duration::from_millis(3000)).await;

    // Kill the sidecar process so the next start gets a completely fresh process.
    if let Err(e) = manager::kill_sidecar().await {
        log::warn!("Failed to kill sidecar on stop: {}", e);
    }

    let mut app = state.lock().await;
    app.trading.status = TradingStatus::Idle;
    app.sidecar_running = false;
    app.connected_to_tws = false;
    drop(app);

    // Notify frontend so event listeners clean up (stop log display, reset indicators)
    let _ = app_handle.emit("sidecar-terminated", serde_json::json!({ "reason": "stop_trading" }));

    Ok("Trading stopped".into())
}

#[tauri::command]
pub async fn emergency_stop(
    app_handle: AppHandle,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    // Send emergency stop to sidecar (cancels orders, closes positions, then disconnects)
    let request = SidecarRequest::new(methods::EMERGENCY_STOP, None);
    let _ = manager::send_request(&request).await;

    // Give the engine time to close all positions (place MKT orders for each)
    tokio::time::sleep(std::time::Duration::from_millis(15000)).await;

    // Force kill sidecar process tree
    if let Err(e) = manager::kill_sidecar().await {
        log::warn!("Failed to kill sidecar on emergency stop: {}", e);
    }

    // Update state: clear positions (closed on TWS), zero unrealized PnL
    let mut app = state.lock().await;
    app.trading.status = TradingStatus::Idle;
    app.sidecar_running = false;
    app.connected_to_tws = false;
    app.trading.positions.clear();
    app.trading.daily_pnl.unrealized = 0.0;
    app.trading.daily_pnl.total = app.trading.daily_pnl.realized;
    drop(app);

    // Notify frontend so event listeners clean up and clear UI (positions, trades, PnL)
    let _ = app_handle.emit("sidecar-terminated", serde_json::json!({ "reason": "emergency_stop" }));

    Ok("Emergency stop executed".into())
}

#[tauri::command]
pub async fn get_trading_status(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    let app = state.lock().await;

    let open_trades = app.trading.positions.len() as i32;
    let closed_trades = app.trading.winning_trades + app.trading.losing_trades;

    Ok(serde_json::json!({
        "status": app.trading.status,
        "sidecar_running": app.sidecar_running,
        "connected_to_tws": app.connected_to_tws,
        "daily_pnl": app.trading.daily_pnl,
        "total_trades": app.trading.total_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
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
