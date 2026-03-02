pub mod commands;
pub mod events;
pub mod license;
pub mod sidecar;
pub mod state;
pub mod utils;

use state::app_state::AppState;
use state::config_state::ConfigState;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

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
            commands::logs::get_logs,
            commands::logs::clear_logs,
            commands::logs::get_log_stats,
        ])
        .setup(|app| {
            let handle = app.handle().clone();

            // ---- Load config from config.json only (single source: trading + settings) ----
            {
                let state_arc = app.state::<Arc<Mutex<AppState>>>().inner().clone();
                let mut app_state = state_arc.blocking_lock();

                match ConfigState::load_config() {
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
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
