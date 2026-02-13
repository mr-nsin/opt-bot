//! License registry: fetch and verify entries signed with Ed25519 (from license-generator).
//! Set REGISTRY_URL and REGISTRY_LICENSE_PUBLIC_KEY_HEX to enable registry validation.

use chrono::{DateTime, Utc};
use ring::signature;
use serde::Deserialize;

use super::hardware_id::get_hardware_id;
use super::validator::{LicenseFeatures, LicenseInfo};

#[derive(Debug, Deserialize)]
pub struct RegistryEntry {
    pub license_key: String,
    pub email: String,
    pub hardware_id: String,
    pub issued_at: String,
    pub expires_at: String,
    pub tier: String,
    pub signature: String,
}

#[derive(Debug, Deserialize)]
pub struct RegistryJson {
    pub licenses: Vec<RegistryEntry>,
}

/// Payload string for verification (must match Python generator).
fn payload_string(
    license_key: &str,
    email: &str,
    hardware_id: &str,
    issued_at: &str,
    expires_at: &str,
    tier: &str,
) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}",
        license_key, email, hardware_id, issued_at, expires_at, tier
    )
}

/// Fetch registry JSON from URL.
pub async fn fetch_registry(url: &str) -> Result<RegistryJson, String> {
    let client = reqwest::Client::builder()
        .build()
        .map_err(|e| format!("HTTP client: {}", e))?;
    let res = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    if !res.status().is_success() {
        return Err(format!("Registry returned status {}", res.status()));
    }
    let body = res.text().await.map_err(|e| format!("Read body: {}", e))?;
    let data: RegistryJson =
        serde_json::from_str(&body).map_err(|e| format!("Parse registry: {}", e))?;
    Ok(data)
}

/// Verify a registry entry with Ed25519 and check hardware + expiry.
/// Returns the entry's data as LicenseInfo for local storage if valid.
pub fn verify_registry_entry(
    entry: &RegistryEntry,
    public_key_hex: &str,
) -> Result<LicenseInfo, String> {
    let public_key_bytes =
        hex::decode(public_key_hex).map_err(|_| "Invalid public key hex (expected 64 chars)")?;
    if public_key_bytes.len() != 32 {
        return Err("Public key must be 32 bytes (64 hex chars)".to_string());
    }

    let payload = payload_string(
        &entry.license_key,
        &entry.email,
        &entry.hardware_id,
        &entry.issued_at,
        &entry.expires_at,
        &entry.tier,
    );
    let message = payload.as_bytes();

    let sig_bytes =
        hex::decode(&entry.signature).map_err(|_| "Invalid signature hex (expected 128 chars)")?;
    if sig_bytes.len() != 64 {
        return Err("Signature must be 64 bytes (128 hex chars)".to_string());
    }

    let peer_public_key =
        signature::UnparsedPublicKey::new(&signature::ED25519, &public_key_bytes[..]);
    peer_public_key
        .verify(message, &sig_bytes[..])
        .map_err(|_| "Invalid signature - license may be tampered".to_string())?;

    let current_hw = get_hardware_id();
    if entry.hardware_id != current_hw {
        return Err("Hardware mismatch - license bound to different machine".to_string());
    }

    let expires_at = DateTime::parse_from_rfc3339(&entry.expires_at)
        .map_err(|e| format!("Invalid expires_at: {}", e))?
        .with_timezone(&Utc);
    if Utc::now() > expires_at {
        return Err("License has expired".to_string());
    }

    let issued_at = DateTime::parse_from_rfc3339(&entry.issued_at)
        .map_err(|e| format!("Invalid issued_at: {}", e))?
        .with_timezone(&Utc);

    let features = LicenseFeatures {
        live_trading: true,
        max_symbols: 20,
        max_daily_trades: 50,
        strategies: vec!["supertrend".into(), "engulfing_atr".into()],
    };

    let mut license = LicenseInfo {
        license_key: entry.license_key.clone(),
        customer_email: entry.email.clone(),
        hardware_id: entry.hardware_id.clone(),
        issued_at,
        expires_at,
        tier: entry.tier.clone(),
        features,
        signature: String::new(),
    };
    license.signature = super::validator::compute_signature_for_local(&license);
    Ok(license)
}
