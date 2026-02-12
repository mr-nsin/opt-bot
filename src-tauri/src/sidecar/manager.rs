use std::sync::Arc;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tokio::sync::Mutex;

use super::protocol::{SidecarMessage, SidecarRequest};
use crate::commands::logs::{push_log, LogEntry};
use crate::state::app_state::AppState;
use crate::state::trading_state::{Position, TradeRecord, TradingStatus};

/// Global sidecar child process handle
static SIDECAR_CHILD: once_cell::sync::Lazy<
    Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,
> = once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(None)));

/// Initialize the sidecar manager (called at app startup)
pub async fn init(_handle: &AppHandle) -> Result<(), String> {
    log::info!("Sidecar manager initialized");
    Ok(())
}

/// Spawn the Python trading engine sidecar
pub async fn spawn_sidecar(handle: &AppHandle) -> Result<(), String> {
    let mut child_lock = SIDECAR_CHILD.lock().await;

    if child_lock.is_some() {
        return Err("Sidecar is already running".into());
    }

    // NOTE:
    // `tauri-plugin-shell`'s `sidecar("name")` expects just the binary *name*.
    // Tauri will automatically resolve this to `src-tauri/binaries/name-<target>`.
    // Our `tauri.conf.json` lists the external bin as "binaries/trading-engine",
    // but the sidecar API should still be called with just "trading-engine".
    let shell = handle.shell();
    let sidecar_command = shell
        .sidecar("trading-engine")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?;

    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    *child_lock = Some(child);
    drop(child_lock);

    // Spawn event listener task
    let app_handle = handle.clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;

        // Get AppState from the managed state so we can update it from sidecar events
        let app_state: Arc<Mutex<AppState>> =
            app_handle.state::<Arc<Mutex<AppState>>>().inner().clone();

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    if let Ok(msg) = serde_json::from_str::<SidecarMessage>(&line_str) {
                        handle_sidecar_message(&app_handle, msg, &app_state).await;
                    } else {
                        log::debug!("Sidecar stdout (non-JSON): {}", line_str);
                    }
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    log::warn!("Sidecar stderr: {}", line_str);
                    let _ = app_handle.emit("sidecar-error", &line_str);

                    // Also push stderr lines to the log buffer
                    push_log(LogEntry {
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        level: "WARN".into(),
                        category: "sidecar".into(),
                        message: line_str.to_string(),
                    })
                    .await;
                }
                CommandEvent::Error(err) => {
                    log::error!("Sidecar error: {}", err);
                    let _ = app_handle.emit("sidecar-error", &err);
                }
                CommandEvent::Terminated(payload) => {
                    log::info!("Sidecar terminated with code: {:?}", payload.code);
                    let _ = app_handle.emit("sidecar-terminated", &payload.code);

                    // Update app state when sidecar dies
                    {
                        let mut app = app_state.lock().await;
                        app.sidecar_running = false;
                        app.trading.status = TradingStatus::Idle;
                        app.connected_to_tws = false;
                    }

                    push_log(LogEntry {
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        level: "WARN".into(),
                        category: "system".into(),
                        message: format!(
                            "Trading engine process terminated (code: {:?})",
                            payload.code
                        ),
                    })
                    .await;

                    // Clean up child handle
                    let mut child_lock = SIDECAR_CHILD.lock().await;
                    *child_lock = None;
                }
                _ => {}
            }
        }
    });

    log::info!("Python sidecar spawned successfully");
    Ok(())
}

/// Send a request to the sidecar
pub async fn send_request(request: &SidecarRequest) -> Result<(), String> {
    let mut child_lock = SIDECAR_CHILD.lock().await;

    if let Some(child) = child_lock.as_mut() {
        let json = serde_json::to_string(request).map_err(|e| format!("Serialize: {}", e))?;
        let msg = format!("{}\n", json);
        child
            .write(msg.as_bytes())
            .map_err(|e| format!("Write to sidecar: {}", e))?;
        Ok(())
    } else {
        Err("Sidecar is not running".into())
    }
}

/// Kill the sidecar process
pub async fn kill_sidecar() -> Result<(), String> {
    let mut child_lock = SIDECAR_CHILD.lock().await;

    if let Some(child) = child_lock.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to kill sidecar: {}", e))?;
        log::info!("Sidecar killed");
    }

    Ok(())
}

/// Check if sidecar is running
pub async fn is_running() -> bool {
    SIDECAR_CHILD.lock().await.is_some()
}

/// Handle incoming messages from the sidecar.
/// Updates the Rust AppState and forwards events to the React frontend.
async fn handle_sidecar_message(
    handle: &AppHandle,
    msg: SidecarMessage,
    state: &Arc<Mutex<AppState>>,
) {
    match msg {
        SidecarMessage::Event(event) => {
            // ---- Update Rust-side AppState based on event type ----
            match event.event.as_str() {
                "pnl_update" => {
                    let daily = event
                        .data
                        .get("daily_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                    let unrealized = event
                        .data
                        .get("unrealized_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                    let realized = event
                        .data
                        .get("realized_pnl")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);

                    let mut app = state.lock().await;
                    app.trading.daily_pnl.total = daily;
                    app.trading.daily_pnl.unrealized = unrealized;
                    app.trading.daily_pnl.realized = realized;
                }

                "position_update" => {
                    if let Ok(pos) = serde_json::from_value::<Position>(event.data.clone()) {
                        let mut app = state.lock().await;
                        if let Some(existing) = app
                            .trading
                            .positions
                            .iter_mut()
                            .find(|p| p.symbol == pos.symbol && p.strike == pos.strike)
                        {
                            *existing = pos;
                        } else {
                            app.trading.positions.push(pos);
                        }
                    }
                }

                "trade_executed" => {
                    if let Ok(trade) = serde_json::from_value::<TradeRecord>(event.data.clone()) {
                        let mut app = state.lock().await;
                        app.trading.total_trades += 1;
                        app.trading.trades_today.push(trade);
                    } else {
                        // Even if we can't fully deserialize, count the trade
                        let mut app = state.lock().await;
                        app.trading.total_trades += 1;
                    }
                }

                "trade_closed" => {
                    let mut app = state.lock().await;
                    if let Some(pnl) = event.data.get("pnl").and_then(|v| v.as_f64()) {
                        if pnl > 0.0 {
                            app.trading.winning_trades += 1;
                        } else {
                            app.trading.losing_trades += 1;
                        }
                    }
                    // Remove from active positions
                    if let Some(symbol) = event.data.get("symbol").and_then(|v| v.as_str()) {
                        app.trading.positions.retain(|p| p.symbol != symbol);
                    }
                }

                "connection_status" => {
                    if let Some(connected) =
                        event.data.get("connected").and_then(|v| v.as_bool())
                    {
                        let mut app = state.lock().await;
                        app.connected_to_tws = connected;
                    }
                }

                "signal_detected" => {
                    let signal_str = serde_json::to_string(&event.data).unwrap_or_default();
                    let mut app = state.lock().await;
                    app.trading.last_signal = Some(signal_str);
                    app.trading.last_signal_time =
                        Some(chrono::Utc::now().to_rfc3339());
                }

                "engine_status" => {
                    if let Some(status_str) =
                        event.data.get("status").and_then(|v| v.as_str())
                    {
                        let mut app = state.lock().await;
                        match status_str {
                            "Running" => app.trading.status = TradingStatus::Running,
                            "Idle" => app.trading.status = TradingStatus::Idle,
                            "Starting" => app.trading.status = TradingStatus::Starting,
                            "Stopping" => app.trading.status = TradingStatus::Stopping,
                            _ => {}
                        }
                        if let Some(connected) =
                            event.data.get("connected").and_then(|v| v.as_bool())
                        {
                            app.connected_to_tws = connected;
                        }
                    }
                }

                "log_message" => {
                    // Push sidecar log messages into the Rust in-memory log buffer
                    let timestamp = event
                        .data
                        .get("timestamp")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    let level = event
                        .data
                        .get("level")
                        .and_then(|v| v.as_str())
                        .unwrap_or("INFO")
                        .to_string();
                    let category = event
                        .data
                        .get("category")
                        .and_then(|v| v.as_str())
                        .unwrap_or("trading")
                        .to_string();
                    let message = event
                        .data
                        .get("message")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();

                    push_log(LogEntry {
                        timestamp,
                        level,
                        category,
                        message,
                    })
                    .await;
                }

                _ => {}
            }

            // ---- Forward ALL events to the React frontend ----
            let event_name = format!("trading:{}", event.event);
            if let Err(e) = handle.emit(&event_name, &event.data) {
                log::error!("Failed to emit event {}: {}", event_name, e);
            }
        }

        SidecarMessage::Response(response) => {
            // Forward responses with a consistent event name
            if let Err(e) = handle.emit("sidecar:response", &response) {
                log::error!("Failed to emit response: {}", e);
            }
        }
    }
}
