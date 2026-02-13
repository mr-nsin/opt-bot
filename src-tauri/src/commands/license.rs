use crate::license::{encrypted_store, hardware_id, registry, validator};
use crate::state::app_state::AppState;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub fn get_hardware_id() -> String {
    hardware_id::get_hardware_id()
}

fn registry_config() -> Option<(String, String)> {
    let url = std::env::var("REGISTRY_URL").ok().filter(|s| !s.is_empty())?;
    let key = std::env::var("REGISTRY_LICENSE_PUBLIC_KEY_HEX").ok().filter(|s| s.len() == 64)?;
    Some((url, key))
}

#[tauri::command]
pub async fn validate_license(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    let license = encrypted_store::load_license()?;
    let status = validator::validate_license(&license).map_err(|e| e.to_string())?;

    // If registry is configured, re-check against it (revocation + expiry)
    if let Some((url, key_hex)) = registry_config() {
        let reg = registry::fetch_registry(&url).await.map_err(|e| {
            format!("Registry check failed: {}. License may be revoked or expired.", e)
        })?;
        let entry = reg
            .licenses
            .iter()
            .find(|e| e.license_key == license.license_key && e.email == license.customer_email)
            .ok_or("License not found in registry (revoked or invalid)")?;
        registry::verify_registry_entry(entry, &key_hex)?;
    }

    let mut app = state.lock().await;
    app.license = Some(license);
    app.licensed = status.valid;

    Ok(status)
}

#[tauri::command]
pub async fn get_license_status(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<serde_json::Value, String> {
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
                Err(e) => Ok(serde_json::json!({
                    "valid": false,
                    "error": e.to_string()
                })),
            },
            Err(e) => Ok(serde_json::json!({
                "valid": false,
                "error": e
            })),
        }
    } else {
        Ok(serde_json::json!({
            "valid": false,
            "error": "No license found"
        }))
    }
}

/// Fallback validity when registry is not configured (dev/local only).
const LICENSE_VALIDITY_DAYS: i64 = 365;

#[tauri::command]
pub async fn activate_license(
    key: String,
    email: String,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    if !validator::validate_key_format(&key) {
        return Err("Invalid license key format. Expected: XXXX-XXXX-XXXX-XXXX".into());
    }

    let license = if let Some((url, key_hex)) = registry_config() {
        // Validate against registry: fetch, find entry, verify Ed25519 + hardware + expiry
        let reg = registry::fetch_registry(&url).await.map_err(|e| {
            format!("Could not reach license registry: {}. Check REGISTRY_URL.", e)
        })?;
        let entry = reg
            .licenses
            .iter()
            .find(|e| e.license_key == key && e.email == email)
            .ok_or("License key or email not found in registry. Get a valid license from the vendor.")?;
        registry::verify_registry_entry(entry, &key_hex)?
    } else {
        // No registry: create local license (dev/offline)
        let features = validator::LicenseFeatures {
            live_trading: true,
            max_symbols: 20,
            max_daily_trades: 50,
            strategies: vec!["supertrend".into(), "engulfing_atr".into()],
        };
        validator::create_license(&key, &email, "pro", LICENSE_VALIDITY_DAYS, features)
    };

    let status = validator::validate_license(&license).map_err(|e| e.to_string())?;
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
