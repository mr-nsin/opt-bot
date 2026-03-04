use crate::commands::logs::{push_log, LogEntry};
use crate::license::{encrypted_store, hardware_id, registry, validator};
use crate::state::app_state::AppState;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Log one message when license is bound to a different machine (exe copied)
fn is_machine_mismatch(err: &str) -> bool {
    let lower = err.to_lowercase();
    lower.contains("another machine")
        || lower.contains("decryption failed")
        || lower.contains("hardware mismatch")
}

/// Ensure we only log "machine mismatch" once per app session
static MACHINE_MISMATCH_LOGGED: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

fn push_machine_mismatch_log() {
    if MACHINE_MISMATCH_LOGGED.swap(true, std::sync::atomic::Ordering::SeqCst) {
        return; // Already logged
    }
    let entry = LogEntry {
        timestamp: chrono::Utc::now().to_rfc3339(),
        level: "ERROR".into(),
        category: "license".into(),
        message: "License is bound to a different machine. This copy cannot be used on this device.".into(),
    };
    tauri::async_runtime::spawn(async move { push_log(entry).await });
}

#[tauri::command]
pub fn get_hardware_id() -> String {
    hardware_id::get_hardware_id()
}

/// Returns email and license key when a valid license is active (for display in UI).
#[tauri::command]
pub async fn get_license_info(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<Option<serde_json::Value>, String> {
    let app = state.lock().await;
    if let Some(ref lic) = app.license {
        if validator::validate_license(lic).is_ok() {
            return Ok(Some(serde_json::json!({
                "email": lic.customer_email,
                "license_key": lic.license_key
            })));
        }
    }
    Ok(None)
}

const DEFAULT_REGISTRY_URL: &str =
    "https://drive.google.com/uc?export=download&id=1_d6-xEbniM2MNqZu1JQtAxrUCsV8-rae";
const DEFAULT_PUBLIC_KEY_HEX: &str =
    "5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821";

fn registry_config() -> Option<(String, String)> {
    let url = std::env::var("REGISTRY_URL")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| DEFAULT_REGISTRY_URL.to_string());
    let key = std::env::var("REGISTRY_LICENSE_PUBLIC_KEY_HEX")
        .ok()
        .map(|s| s.trim().replace("0x", "").replace("0X", ""))
        .filter(|s| s.len() == 64)
        .unwrap_or_else(|| DEFAULT_PUBLIC_KEY_HEX.to_string());
    Some((url, key))
}

const REGISTRY_REQUIRED_MSG: &str = "License registry is not configured. Set REGISTRY_URL and REGISTRY_LICENSE_PUBLIC_KEY_HEX. Contact your administrator.";

#[tauri::command]
pub async fn validate_license(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    let (url, key_hex) = registry_config()
        .ok_or_else(|| REGISTRY_REQUIRED_MSG.to_string())?;

    let license = encrypted_store::load_license().map_err(|e| {
        if is_machine_mismatch(&e) {
            push_machine_mismatch_log();
        }
        e
    })?;

    // Re-check against registry and use registry's expiry (so days_remaining matches registry, not stale local file)
    let reg = registry::fetch_registry(&url).await.map_err(|e| {
        format!("Registry check failed: {}. License may be revoked or expired.", e)
    })?;
    let entry = reg
        .licenses
        .iter()
        .find(|e| e.license_key == license.license_key && e.email == license.customer_email)
        .ok_or("License not found in registry (revoked or invalid)")?;
    let license_from_registry = registry::verify_registry_entry(entry, &key_hex).map_err(|e| {
        if is_machine_mismatch(&e) {
            push_machine_mismatch_log();
        }
        e
    })?;

    // Status from registry license so days_remaining / expires_at match the registry (e.g. 30 days)
    let status = validator::validate_license(&license_from_registry).map_err(|e| {
        let err_str = e.to_string();
        if is_machine_mismatch(&err_str) {
            push_machine_mismatch_log();
        }
        err_str
    })?;

    // Keep local file in sync with registry expiry
    let _ = encrypted_store::save_license(&license_from_registry);

    let mut app = state.lock().await;
    app.license = Some(license_from_registry);
    app.licensed = status.valid;

    Ok(status)
}

#[tauri::command]
pub async fn get_license_status(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
    if registry_config().is_none() {
        return Ok(serde_json::json!({
            "valid": false,
            "error": REGISTRY_REQUIRED_MSG
        }));
    }

    let app = state.lock().await;

    if let Some(ref license) = app.license {
        match validator::validate_license(license) {
            Ok(status) => Ok(serde_json::to_value(&status).unwrap()),
            Err(e) => Ok(serde_json::json!({
                "valid": false,
                "error": e.to_string()
            })),
        }
    } else if encrypted_store::license_exists() {
        // License file exists but not loaded yet
        match encrypted_store::load_license() {
            Ok(license) => match validator::validate_license(&license) {
                Ok(status) => Ok(serde_json::to_value(&status).unwrap()),
                Err(e) => {
                    let err_str = e.to_string();
                    if is_machine_mismatch(&err_str) {
                        push_machine_mismatch_log();
                    }
                    Ok(serde_json::json!({
                        "valid": false,
                        "error": err_str
                    }))
                }
            },
            Err(e) => {
                if is_machine_mismatch(&e) {
                    push_machine_mismatch_log();
                }
                Ok(serde_json::json!({
                    "valid": false,
                    "error": e
                }))
            }
        }
    } else {
        Ok(serde_json::json!({
            "valid": false,
            "error": "No license found"
        }))
    }
}

#[tauri::command]
pub async fn activate_license(
    key: String,
    email: String,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    if !validator::validate_key_format(&key) {
        return Err("Invalid license key format. Expected: XXXX-XXXX-XXXX-XXXX".into());
    }

    let (url, key_hex) = registry_config()
        .ok_or_else(|| REGISTRY_REQUIRED_MSG.to_string())?;

    // Validate against registry: fetch, find entry, verify Ed25519 + hardware + expiry
    let reg = registry::fetch_registry(&url).await.map_err(|e| {
        format!("Could not reach license registry: {}. Check REGISTRY_URL.", e)
    })?;
    let entry = reg
        .licenses
        .iter()
        .find(|e| e.license_key == key && e.email == email)
        .ok_or("License key or email not found in registry. Get a valid license from the vendor.")?;
    let license = registry::verify_registry_entry(entry, &key_hex).map_err(|e| {
        if is_machine_mismatch(&e) {
            push_machine_mismatch_log();
        }
        e
    })?;

    let status = validator::validate_license(&license).map_err(|e| {
        let err_str = e.to_string();
        if is_machine_mismatch(&err_str) {
            push_machine_mismatch_log();
        }
        err_str
    })?;
    encrypted_store::save_license(&license)?;

    let mut app = state.lock().await;
    app.license = Some(license);
    app.licensed = true;

    Ok(status)
}

#[tauri::command]
pub async fn deactivate_license(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    encrypted_store::delete_license()?;

    let mut app = state.lock().await;
    app.license = None;
    app.licensed = false;

    Ok(())
}

/// Invalidates the license when revoked (e.g. key removed from registry).
/// Deletes local license file and clears app state so the user sees the license gate.
/// Called when validate fails with "not found in registry".
#[tauri::command]
pub async fn invalidate_license_state(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    // Delete local license so next check has no stale data
    let _ = encrypted_store::delete_license();

    let mut app = state.lock().await;
    app.license = None;
    app.licensed = false;

    Ok(())
}
