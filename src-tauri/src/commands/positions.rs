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
    _state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<String, String> {
    if !manager::is_running().await {
        return Err("Trading engine is not running".into());
    }

    let request = SidecarRequest::new(
        methods::CLOSE_POSITION,
        Some(serde_json::json!({ "symbol": symbol })),
    );

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
