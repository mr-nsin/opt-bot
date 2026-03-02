use sha2::{Digest, Sha256};
use sysinfo::System;

/// Normalize a string for fingerprint: trim, lowercase, collapse whitespace.
/// Reduces false mismatches from minor hostname/OS display changes.
fn normalize(s: &str) -> String {
    s.trim()
        .to_lowercase()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

/// Get primary MAC address for hardware binding (more stable than hostname alone).
fn primary_mac() -> String {
    mac_address::get_mac_address()
        .ok()
        .flatten()
        .map(|m| normalize(&m.to_string()))
        .unwrap_or_else(|| "unknown".into())
}

/// Generate a unique hardware fingerprint for this machine.
/// Combines hostname, CPU brand, total memory, OS info, and MAC address into a SHA-256 hash.
/// Bound to one machine: copying the license file to another PC will not work
/// (different hardware_id and different decryption key).
pub fn get_hardware_id() -> String {
    let sys = System::new_all();

    let hostname = normalize(&System::host_name().unwrap_or_else(|| "unknown".into()));
    let cpu_brand = sys
        .cpus()
        .first()
        .map(|c| normalize(c.brand()))
        .unwrap_or_else(|| "unknown".into());
    let total_memory = sys.total_memory();
    let os_name = normalize(&System::name().unwrap_or_else(|| "unknown".into()));
    let os_version = normalize(&System::os_version().unwrap_or_else(|| "unknown".into()));
    let mac = primary_mac();

    let fingerprint = format!(
        "{}|{}|{}|{}|{}|{}|quantdrift-salt-v1",
        hostname, cpu_brand, total_memory, os_name, os_version, mac
    );

    let mut hasher = Sha256::new();
    hasher.update(fingerprint.as_bytes());
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hardware_id_consistency() {
        let id1 = get_hardware_id();
        let id2 = get_hardware_id();
        assert_eq!(id1, id2);
        assert_eq!(id1.len(), 64); // SHA-256 hex
    }
}
