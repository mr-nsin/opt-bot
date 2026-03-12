use crate::sidecar::{manager, protocol::*};
use crate::state::app_state::AppState;
use crate::state::trading_state::Position;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub async fn get_positions(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    // When sidecar is running, fetch live positions from IBKR via the trading engine
    if manager::is_running().await {
        let request = SidecarRequest::new(methods::GET_POSITIONS, None);
        match manager::send_request_and_wait(&request).await {
            Ok(result) => {
                // Parse positions array from sidecar response; normalize "qty" -> "quantity" for compatibility
                let positions: Vec<Position> = if let Some(arr) = result.as_array() {
                    arr.iter()
                        .filter_map(|v| {
                            let mut obj = v.clone();
                            if obj.get("quantity").is_none() {
                                if let Some(q) = obj.get("qty").and_then(|q| q.as_i64()) {
                                    obj["quantity"] = serde_json::json!(q);
                                }
                            }
                            serde_json::from_value(obj).ok()
                        })
                        .collect()
                } else {
                    vec![]
                };
                let mut app = state.lock().await;
                // Only replace when we have a non-empty result. When engine returns [] (e.g. TWS sync
                // delay, account filter) or parsing fails, preserve event-populated positions so the
                // UI doesn't wipe positions that were correctly added via position_update events.
                if !positions.is_empty() {
                    app.trading.positions = positions;
                }
                return serde_json::to_value(&app.trading.positions).map_err(|e| e.to_string());
            }
            Err(e) => {
                // Fall through to return cached positions on timeout or error
                log::warn!("get_positions: failed to fetch from sidecar: {}", e);
            }
        }
    }

    let app = state.lock().await;
    serde_json::to_value(&app.trading.positions).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn close_position(
    symbol: String,
    strike: Option<f64>,
    right: Option<String>,
    expiry: Option<String>,
    _state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    if !manager::is_running().await {
        return Err("Trading engine is not running".into());
    }

    let mut params = serde_json::json!({ "symbol": symbol });
    if let Some(s) = strike {
        params["strike"] = serde_json::json!(s);
    }
    if let Some(r) = right {
        params["right"] = serde_json::json!(r);
    }
    if let Some(e) = expiry {
        params["expiry"] = serde_json::json!(e);
    }

    let request = SidecarRequest::new(methods::CLOSE_POSITION, Some(params));
    manager::send_request(&request).await?;
    Ok(format!("Close position request sent for {}", symbol))
}

#[tauri::command]
pub async fn close_all_positions(
    _state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    if !manager::is_running().await {
        return Err("Trading engine is not running".into());
    }

    let request = SidecarRequest::new(methods::CLOSE_ALL, None);
    manager::send_request(&request).await?;

    Ok("Close all positions request sent".into())
}

#[tauri::command]
pub async fn close_calls_positions(
    _state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    if !manager::is_running().await {
        return Err("Trading engine is not running".into());
    }

    let request = SidecarRequest::new(methods::CLOSE_CALLS, None);
    manager::send_request(&request).await?;

    Ok("Close all calls request sent".into())
}

#[tauri::command]
pub async fn close_puts_positions(
    _state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    if !manager::is_running().await {
        return Err("Trading engine is not running".into());
    }

    let request = SidecarRequest::new(methods::CLOSE_PUTS, None);
    manager::send_request(&request).await?;

    Ok("Close all puts request sent".into())
}
