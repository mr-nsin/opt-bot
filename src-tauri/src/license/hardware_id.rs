use sha2::{Digest, Sha256};
use sysinfo::System;

/// Generate a unique hardware fingerprint for this machine.
/// Combines hostname, CPU brand, total memory, and OS info into a SHA-256 hash.
pub fn get_hardware_id() -> String {
    let sys = System::new_all();

    let hostname = System::host_name().unwrap_or_else(|| "unknown".into());
    let cpu_brand = sys
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "unknown".into());
    let total_memory = sys.total_memory();
    let os_name = System::name().unwrap_or_else(|| "unknown".into());
    let os_version = System::os_version().unwrap_or_else(|| "unknown".into());

    let fingerprint = format!(
        "{}|{}|{}|{}|{}|quantdrift-salt-v1",
        hostname, cpu_brand, total_memory, os_name, os_version
    );

    let mut hasher = Sha256::new();
    hasher.update(fingerprint.as_bytes());
    let result = hasher.finalize();
    hex::encode(result)
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
