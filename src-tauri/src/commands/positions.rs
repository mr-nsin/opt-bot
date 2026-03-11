use crate::sidecar::{manager, protocol::*};
use crate::state::app_state::AppState;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub async fn get_positions(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
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
