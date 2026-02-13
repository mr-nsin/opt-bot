use chrono::{DateTime, Utc};
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use super::hardware_id::get_hardware_id;

type HmacSha256 = Hmac<Sha256>;

/// Default HMAC secret (dev fallback). In production, set LICENSE_HMAC_SECRET
/// at build or runtime so the secret is not in source.
const HMAC_SECRET_DEFAULT: &[u8] = b"quantdrift-license-hmac-secret-v1-2026";

fn hmac_secret() -> Vec<u8> {
    std::env::var("LICENSE_HMAC_SECRET")
        .ok()
        .filter(|s| s.len() >= 32)
        .map(|s| s.into_bytes())
        .unwrap_or_else(|| HMAC_SECRET_DEFAULT.to_vec())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseFeatures {
    pub live_trading: bool,
    pub max_symbols: i32,
    pub max_daily_trades: i32,
    pub strategies: Vec<String>,
}

impl Default for LicenseFeatures {
    fn default() -> Self {
        Self {
            live_trading: false,
            max_symbols: 5,
            max_daily_trades: 10,
            strategies: vec!["supertrend".into()],
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseInfo {
    pub license_key: String,
    pub customer_email: String,
    pub hardware_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub tier: String,
    pub features: LicenseFeatures,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseStatus {
    pub valid: bool,
    pub tier: String,
    pub days_remaining: i64,
    pub expires_at: String,
    pub features: LicenseFeatures,
    pub hardware_bound: bool,
    pub error: Option<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum LicenseError {
    #[error("License key is invalid")]
    InvalidKey,
    #[error("License has expired")]
    Expired,
    #[error("Hardware mismatch - license bound to different machine")]
    HardwareMismatch,
    #[error("Invalid signature - license may be tampered")]
    InvalidSignature,
    #[error("License file not found")]
    NotFound,
    #[error("License file corrupt: {0}")]
    Corrupt(String),
}

/// Compute the HMAC-SHA256 signature for a license (used for local storage).
/// Uses LICENSE_HMAC_SECRET env var if set (>= 32 chars), else default (dev).
pub fn compute_signature_for_local(license: &LicenseInfo) -> String {
    compute_signature(license)
}

fn compute_signature(license: &LicenseInfo) -> String {
    let data = format!(
        "{}|{}|{}|{}|{}|{}",
        license.license_key,
        license.customer_email,
        license.hardware_id,
        license.issued_at.to_rfc3339(),
        license.expires_at.to_rfc3339(),
        license.tier,
    );

    let secret = hmac_secret();
    let mut mac = HmacSha256::new_from_slice(&secret).expect("HMAC key valid");
    mac.update(data.as_bytes());
    hex::encode(mac.finalize().into_bytes())
}

/// Validate a license fully: signature, hardware, expiry
pub fn validate_license(license: &LicenseInfo) -> Result<LicenseStatus, LicenseError> {
    // 1. Verify HMAC signature
    let expected_sig = compute_signature(license);
    if license.signature != expected_sig {
        return Err(LicenseError::InvalidSignature);
    }

    // 2. Check hardware ID
    let current_hw_id = get_hardware_id();
    if license.hardware_id != current_hw_id {
        return Err(LicenseError::HardwareMismatch);
    }

    // 3. Check expiry
    let now = Utc::now();
    if now > license.expires_at {
        return Err(LicenseError::Expired);
    }

    // num_days() counts full 24h periods, so e.g. 23h left → 0. Show at least 1 day when any time remains.
    let raw_days = (license.expires_at - now).num_days();
    let days_remaining = if raw_days == 0 { 1 } else { raw_days };

    Ok(LicenseStatus {
        valid: true,
        tier: license.tier.clone(),
        days_remaining,
        expires_at: license.expires_at.to_rfc3339(),
        features: license.features.clone(),
        hardware_bound: true,
        error: None,
    })
}

/// Generate a signed license (used for activation)
pub fn create_license(
    key: &str,
    email: &str,
    tier: &str,
    validity_days: i64,
    features: LicenseFeatures,
) -> LicenseInfo {
    let now = Utc::now();
    let expires = now + chrono::Duration::days(validity_days);
    let hw_id = get_hardware_id();

    let mut license = LicenseInfo {
        license_key: key.to_string(),
        customer_email: email.to_string(),
        hardware_id: hw_id,
        issued_at: now,
        expires_at: expires,
        tier: tier.to_string(),
        features,
        signature: String::new(),
    };

    license.signature = compute_signature(&license);
    license
}

/// Simple key format validation (XXXX-XXXX-XXXX-XXXX)
pub fn validate_key_format(key: &str) -> bool {
    let parts: Vec<&str> = key.split('-').collect();
    if parts.len() != 4 {
        return false;
    }
    parts.iter().all(|p| p.len() == 4 && p.chars().all(|c| c.is_alphanumeric()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_and_validate() {
        let features = LicenseFeatures {
            live_trading: true,
            max_symbols: 20,
            max_daily_trades: 50,
            strategies: vec!["supertrend".into(), "engulfing_atr".into()],
        };

        let license = create_license("TEST-1234-ABCD-5678", "test@test.com", "pro", 90, features);

        let result = validate_license(&license);
        assert!(result.is_ok());

        let status = result.unwrap();
        assert!(status.valid);
        assert_eq!(status.tier, "pro");
        assert!(status.days_remaining >= 89);
    }

    #[test]
    fn test_key_format() {
        assert!(validate_key_format("ABCD-1234-EFGH-5678"));
        assert!(!validate_key_format("invalid"));
        assert!(!validate_key_format("AB-1234-EFGH-5678"));
    }
}
