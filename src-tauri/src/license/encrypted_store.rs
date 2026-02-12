use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;

use super::hardware_id::get_hardware_id;
use super::validator::LicenseInfo;

const NONCE_SIZE: usize = 12;

#[derive(Serialize, Deserialize)]
struct EncryptedLicense {
    nonce: String, // hex-encoded
    data: String,  // hex-encoded encrypted payload
    version: u32,
}

/// Derive an AES-256 key from the hardware ID
fn derive_key() -> [u8; 32] {
    let hw_id = get_hardware_id();
    let salt = b"quantdrift-aes-key-derivation-v1";
    let input = format!("{}|{}", hw_id, hex::encode(salt));

    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    let result = hasher.finalize();

    let mut key = [0u8; 32];
    key.copy_from_slice(&result);
    key
}

/// Get the path to the license file
fn license_path() -> PathBuf {
    let mut path = directories::ProjectDirs::from("com", "quantdrift", "optbot")
        .map(|dirs| dirs.data_dir().to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."));

    if !path.exists() {
        fs::create_dir_all(&path).ok();
    }

    path.push("license.enc");
    path
}

/// Save a license to an encrypted file (bound to this hardware)
pub fn save_license(license: &LicenseInfo) -> Result<(), String> {
    let key = derive_key();
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|e| format!("Cipher init: {}", e))?;

    let mut nonce_bytes = [0u8; NONCE_SIZE];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let plaintext = serde_json::to_string(license).map_err(|e| format!("Serialize: {}", e))?;

    let ciphertext = cipher
        .encrypt(nonce, plaintext.as_bytes())
        .map_err(|e| format!("Encrypt: {}", e))?;

    let encrypted = EncryptedLicense {
        nonce: hex::encode(nonce_bytes),
        data: hex::encode(ciphertext),
        version: 1,
    };

    let json = serde_json::to_string_pretty(&encrypted).map_err(|e| format!("Serialize: {}", e))?;

    let path = license_path();
    fs::write(&path, json).map_err(|e| format!("Write file: {}", e))?;

    log::info!("License saved to {:?}", path);
    Ok(())
}

/// Load and decrypt a license from the encrypted file
pub fn load_license() -> Result<LicenseInfo, String> {
    let path = license_path();

    if !path.exists() {
        return Err("License file not found".into());
    }

    let contents = fs::read_to_string(&path).map_err(|e| format!("Read file: {}", e))?;

    let encrypted: EncryptedLicense =
        serde_json::from_str(&contents).map_err(|e| format!("Parse: {}", e))?;

    let key = derive_key();
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|e| format!("Cipher init: {}", e))?;

    let nonce_bytes = hex::decode(&encrypted.nonce).map_err(|e| format!("Decode nonce: {}", e))?;
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext =
        hex::decode(&encrypted.data).map_err(|e| format!("Decode ciphertext: {}", e))?;

    let plaintext = cipher
        .decrypt(nonce, ciphertext.as_ref())
        .map_err(|_| "Decryption failed - license may be from another machine".to_string())?;

    let license: LicenseInfo = serde_json::from_slice(&plaintext)
        .map_err(|e| format!("Deserialize license: {}", e))?;

    Ok(license)
}

/// Delete the stored license
pub fn delete_license() -> Result<(), String> {
    let path = license_path();
    if path.exists() {
        fs::remove_file(&path).map_err(|e| format!("Delete: {}", e))?;
    }
    Ok(())
}

/// Check if a license file exists
pub fn license_exists() -> bool {
    license_path().exists()
}
