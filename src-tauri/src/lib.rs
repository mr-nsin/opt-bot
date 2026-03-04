pub mod commands;
pub mod events;
pub mod license;
pub mod sidecar;
pub mod state;
pub mod utils;

use state::app_state::AppState;
use state::config_state::ConfigState;
use state::trading_state::TradingStatus;
use std::sync::Arc;
use tauri::{Emitter, Manager};
use tokio::sync::Mutex;

#[tauri::command]
async fn confirm_close(app_handle: tauri::AppHandle) -> Result<(), String> {
    if let Err(e) = sidecar::manager::kill_sidecar().await {
        log::warn!("Failed to kill trading engine on confirmed close: {}", e);
    }
    app_handle.exit(0);
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();

    let app_state = Arc::new(Mutex::new(AppState::new()));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            // License commands
            commands::license::validate_license,
            commands::license::get_license_status,
            commands::license::activate_license,
            commands::license::deactivate_license,
            commands::license::invalidate_license_state,
            commands::license::get_hardware_id,
            commands::license::get_license_info,
            // Trading commands
            commands::trading::start_trading,
            commands::trading::stop_trading,
            commands::trading::emergency_stop,
            commands::trading::get_trading_status,
            commands::trading::get_account_metrics,
            commands::trading::simulate_demo,
            // Config commands
            commands::config::get_config,
            commands::config::save_config,
            commands::config::get_settings,
            commands::config::save_settings,
            commands::config::get_settings_file,
            // Position commands
            commands::positions::get_positions,
            commands::positions::close_position,
            commands::positions::close_all_positions,
            // Log commands
            commands::logs::push_log_entry,
            commands::logs::get_logs,
            commands::logs::get_logs_dir,
            commands::logs::clear_logs,
            commands::logs::get_log_stats,
            // Close confirmation
            confirm_close,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let app_handle = window.app_handle().clone();
                let state_arc = app_handle.state::<Arc<Mutex<AppState>>>().inner().clone();

                // Check if trading engine is active (non-blocking try_lock)
                let is_trading = state_arc
                    .try_lock()
                    .map(|app| {
                        matches!(app.trading.status, TradingStatus::Running | TradingStatus::Starting)
                            || app.sidecar_running
                    })
                    .unwrap_or(false);

                if is_trading {
                    // Prevent the window from closing immediately
                    api.prevent_close();
                    // Tell the frontend to show a confirmation dialog
                    let _ = app_handle.emit("close-requested", ());
                } else {
                    // Not trading: kill sidecar (if any) and let the window close
                    tauri::async_runtime::block_on(async {
                        let _ = sidecar::manager::kill_sidecar().await;
                    });
                }
            }
        })
        .setup(|app| {
            let handle = app.handle().clone();

            // ---- Load config from config.json only (single source: trading + settings) ----
            {
                let state_arc = app.state::<Arc<Mutex<AppState>>>().inner().clone();
                let mut app_state = state_arc.blocking_lock();

                // Use bundled resource path when running as exe (config.json in resources/)
                let resource_path = app.path().resource_dir().ok().map(|d| d.join("config.json"));
                match ConfigState::load_config_with_resource_path(resource_path) {
                    Some(full_config) => {
                        app_state.config = full_config;
                        log::info!(
                            "Loaded config from config.json ({} symbols)",
                            app_state.config.trading.stock_list_to_trade.len()
                        );
                    }
                    None => log::info!("No config.json found, using defaults"),
                }
            }

            // ---- Spawn async initialization tasks ----
            tauri::async_runtime::spawn(async move {
                log::info!("QuantDrift Options Trading Bot started");

                // Push startup log entry to the in-memory buffer
                commands::logs::push_log(commands::logs::LogEntry {
                    timestamp: chrono::Utc::now().to_rfc3339(),
                    level: "INFO".into(),
                    category: "system".into(),
                    message: "QuantDrift Options Trading Bot started".into(),
                })
                .await;

                // Start health monitor for sidecar process
                sidecar::health::start_health_monitor(handle.clone()).await;

                // Initialize sidecar manager
                if let Err(e) = sidecar::manager::init(&handle).await {
                    log::error!("Failed to initialize sidecar manager: {}", e);
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| {
            match &event {
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                    // Final safety net: kill trading engine on any exit path
                    tauri::async_runtime::block_on(async {
                        let _ = sidecar::manager::kill_sidecar().await;
                    });
                }
                _ => {}
            }
        });
}
