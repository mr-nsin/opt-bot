use crate::utils::paths;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: String,
    pub level: String,
    pub category: String,
    pub message: String,
}

/// In-memory log buffer (ring buffer of recent logs)
static LOG_BUFFER: once_cell::sync::Lazy<Arc<Mutex<Vec<LogEntry>>>> =
    once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(Vec::with_capacity(1000))));

/// Add a log entry to the buffer (called by event router)
pub async fn push_log(entry: LogEntry) {
    let mut buffer = LOG_BUFFER.lock().await;
    if buffer.len() >= 1000 {
        buffer.remove(0);
    }
    buffer.push(entry);
}

/// Push a log entry from the frontend (e.g. license invalidation message)
#[tauri::command]
pub async fn push_log_entry(
    message: String,
    level: Option<String>,
    category: Option<String>,
) -> Result<(), String> {
    let level = level.unwrap_or_else(|| "INFO".into());
    let category = category.unwrap_or_else(|| "system".into());
    push_log(LogEntry {
        timestamp: chrono::Utc::now().to_rfc3339(),
        level,
        category,
        message,
    })
    .await;
    Ok(())
}

#[tauri::command]
pub async fn get_logs(
    level: Option<String>,
    category: Option<String>,
    limit: Option<usize>,
) -> Result<Vec<LogEntry>, String> {
    let buffer = LOG_BUFFER.lock().await;
    let limit = limit.unwrap_or(60);

    // Collect last `limit` entries that pass filter, in chronological order (oldest first) so UI shows latest at bottom
    let mut filtered: Vec<LogEntry> = buffer
        .iter()
        .rev()
        .filter(|log| {
            let level_match = level
                .as_ref()
                .map(|l| log.level.eq_ignore_ascii_case(l))
                .unwrap_or(true);
            let cat_match = category
                .as_ref()
                .map(|c| log.category.eq_ignore_ascii_case(c))
                .unwrap_or(true);
            level_match && cat_match
        })
        .take(limit)
        .cloned()
        .collect();
    filtered.reverse();
    Ok(filtered)
}

#[tauri::command]
pub async fn clear_logs() -> Result<String, String> {
    let mut buffer = LOG_BUFFER.lock().await;
    buffer.clear();
    Ok("Logs cleared".into())
}

#[tauri::command]
pub async fn get_logs_dir() -> Result<String, String> {
    let path = paths::logs_dir();
    path.to_str()
        .map(String::from)
        .ok_or_else(|| "Unable to resolve logs path".to_string())
}

#[tauri::command]
pub async fn get_log_stats() -> Result<serde_json::Value, String> {
    let buffer = LOG_BUFFER.lock().await;

    let total = buffer.len();
    let errors = buffer.iter().filter(|l| l.level == "ERROR").count();
    let warnings = buffer.iter().filter(|l| l.level == "WARN").count();
    let info = buffer.iter().filter(|l| l.level == "INFO").count();

    Ok(serde_json::json!({
        "total": total,
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }))
}
