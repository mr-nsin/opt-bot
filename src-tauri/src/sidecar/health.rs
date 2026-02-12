use std::time::{Duration, Instant};
use tauri::Emitter;

use super::manager;
use super::protocol::{methods, SidecarRequest};

/// Health check interval
const HEALTH_CHECK_INTERVAL: Duration = Duration::from_secs(30);

/// Start periodic health checks on the sidecar
pub async fn start_health_monitor(handle: tauri::AppHandle) {
    tauri::async_runtime::spawn(async move {
        let mut _last_check = Instant::now();

        loop {
            tokio::time::sleep(HEALTH_CHECK_INTERVAL).await;

            if !manager::is_running().await {
                continue;
            }

            let request = SidecarRequest::new(methods::PING, None);

            if let Err(e) = manager::send_request(&request).await {
                log::warn!("Sidecar health check failed: {}", e);
                let _ = handle.emit(
                    "sidecar-health",
                    serde_json::json!({ "healthy": false, "error": e }),
                );
            } else {
                let _ = handle.emit(
                    "sidecar-health",
                    serde_json::json!({ "healthy": true }),
                );
            }

            _last_check = Instant::now();
        }
    });
}
