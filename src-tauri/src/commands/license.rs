use crate::license::{encrypted_store, validator};
use crate::state::app_state::AppState;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tauri::command]
pub async fn validate_license(
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    // Try to load existing license
    let license = encrypted_store::load_license()?;

    // Validate it
    let status = validator::validate_license(&license).map_err(|e| e.to_string())?;

    // Update app state
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

#[tauri::command]
pub async fn activate_license(
    key: String,
    email: String,
    state: tauri::State<'_, Arc<Mutex<AppState>>>,
) -> Result<validator::LicenseStatus, String> {
    // Validate key format
    if !validator::validate_key_format(&key) {
        return Err("Invalid license key format. Expected: XXXX-XXXX-XXXX-XXXX".into());
    }

    // Create a new license (in a real app, this would validate against a server)
    let features = validator::LicenseFeatures {
        live_trading: true,
        max_symbols: 20,
        max_daily_trades: 50,
        strategies: vec!["supertrend".into(), "engulfing_atr".into()],
    };

    let license = validator::create_license(&key, &email, "pro", 90, features);

    // Validate the license we just created
    let status = validator::validate_license(&license).map_err(|e| e.to_string())?;

    // Save encrypted to disk
    encrypted_store::save_license(&license)?;

    // Update state
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
