# QuantDrift Licensing System

## Overview

Licensing is implemented in the **Rust backend** (Tauri). It is **bound to one machine** using a hardware fingerprint and **never trusts the frontend** for license state.

---

## How It Works

### 1. **Hardware binding (one machine only)**

- **Hardware ID** is computed in `src-tauri/src/license/hardware_id.rs`.
- It hashes a fingerprint built from:
  - Hostname
  - CPU brand (first core)
  - Total physical memory
  - OS name and version
  - A fixed salt (`quantdrift-salt-v1`)
- Result is a **SHA-256 hex string** (64 chars). Same machine → same ID; different machine or major hardware change → different ID.

### 2. **License creation (activation)**

- User enters **license key** (format `XXXX-XXXX-XXXX-XXXX`) and **email** in the UI.
- Backend (`activate_license` command):
  1. Validates key format.
  2. Calls `validator::create_license(...)` which:
     - Takes **current machine’s hardware ID**.
     - Builds a license with: key, email, tier, expiry, features, **hardware_id**.
     - Signs it with **HMAC-SHA256** (secret in Rust; frontend never sees it).
  3. Saves the license via **encrypted_store** (see below).
  4. Updates in-memory app state so the app is “licensed”.

So **every activated license is tied to the machine that activated it** (its hardware ID is inside the signed payload).

### 3. **Encrypted storage**

- **File:** `license.enc` in the app data directory (e.g. macOS `~/Library/Application Support/com.quantdrift.optbot/`).
- **Encryption:** AES-256-GCM.
- **Key derivation:** Key is derived from **current machine’s hardware ID** + salt. So:
  - On **this** machine: same hardware ID → same key → decrypt OK.
  - On **another** machine: different hardware ID → different key → decryption fails (file is useless there).
- Even if someone copies `license.enc` to another PC, it cannot be decrypted there.

### 4. **Validation (on startup and when needed)**

- **validate_license** (e.g. on app load):
  1. Load license from disk (decrypt with hardware-derived key).
  2. **Signature:** Recompute HMAC over license fields; reject if it doesn’t match (tampering).
  3. **Hardware:** Compare `license.hardware_id` with **current** `get_hardware_id()`. If different → `HardwareMismatch` (wrong machine).
  4. **Expiry:** Reject if `now > expires_at`.
- If any check fails, the app is not licensed (gate shows activate screen).

---

## Security Properties

| Property | How it’s enforced |
|--------|---------------------|
| **One machine only** | License stores `hardware_id`; validation requires it to match current machine. Encrypted file is bound to the same machine via AES key derived from hardware ID. |
| **No copy-paste to another PC** | Different hardware → different key → decrypt fails; and/or `hardware_id` mismatch. |
| **Tamper-resistant** | HMAC over key, email, hardware_id, dates, tier. Changing any field invalidates the signature. |
| **Expiry** | Checked in Rust; frontend only displays what backend returns. |
| **Secret not in frontend** | HMAC secret and AES derivation stay in Rust; frontend only sends key/email and shows status. |

---

## Flow Summary

```
[User enters key + email]
        ↓
[Rust: activate_license]
        ↓
  create_license() → hardware_id = get_hardware_id()  ← current machine only
        ↓
  signature = HMAC(key, email, hardware_id, dates, tier)
        ↓
  save_license() → encrypt with key = f(hardware_id)   ← same machine only
        ↓
[License stored and app marked licensed]

--- Later (e.g. restart) ---

[Rust: validate_license]
        ↓
  load_license() → decrypt with key = f(current_hardware_id)  ← fails on other machine
        ↓
  verify signature, hardware_id == get_hardware_id(), not expired
        ↓
[Valid → app runs; invalid → show activate screen]
```

---

## Hardening Implemented

1. **HMAC secret** – The app reads `LICENSE_HMAC_SECRET` at runtime (must be ≥ 32 chars). If set, that value is used instead of the default. For production builds, set this env var so the secret is not in source.
2. **Hardware ID normalization** – Hostname, CPU brand, OS name, and OS version are normalized (trim, lowercase, collapse whitespace) so minor display or config changes don't invalidate an existing license on the same machine.

## Optional / Future Hardening

1. **Activation is offline**: any key in format `XXXX-XXXX-XXXX-XXXX` creates a valid license. For real products, add a **license server** that checks key/email and returns a signed token; the app only accepts server-signed licenses.
2. **Hardware ID** can still change if the user changes hostname, OS version, or (theoretically) CPU/RAM. You can add a “grace” re-activation or more stable identifiers (e.g. disk serial, MAC) with care for privacy and stability.
3. **Re-validation**: On startup and every 4 hours the app calls `validate_license`, which re-checks the registry when REGISTRY_URL is set (revocation/expiry).

---

## Registry-based licensing (license-generator)

For **vendor-controlled** licensing with validity embedded in a **registry file** (e.g. on Drive or a server):

1. **Python generator** (`license-generator/`) – Run only on your machine. Inputs: **hardware_id** (from customer’s app), **email**, **validity (days)**. Creates an Ed25519-signed license entry and **appends** it to a registry JSON file. Output: **license key** (XXXX-XXXX-XXXX-XXXX) to give to the customer. See `license-generator/README.md`.

2. **Registry file** – Single JSON file (e.g. `license_registry.json`) with a `licenses` array. Upload or sync to Drive or a web server; app fetches via URL.

3. **App env vars** – Set when running the app: **REGISTRY_URL** (URL to the registry JSON), **REGISTRY_LICENSE_PUBLIC_KEY_HEX** (64-char hex of Ed25519 public key; get via `python generate_license.py --export-public-key`).

4. **Activation** – When both are set, app fetches registry, finds entry by key+email, verifies Ed25519, checks hardware_id and expiry, then saves license locally. Validity is embedded in the registry entry.

5. **Revocation** – Remove the entry from the registry and re-upload; app treats the license as invalid on the next check (startup or every 4 hours).

---

## Files Reference

| File | Role |
|------|------|
| `src-tauri/src/license/hardware_id.rs` | Computes machine fingerprint (one-machine binding). |
| `src-tauri/src/license/validator.rs` | Creates license, HMAC signature, validates signature/hardware/expiry. |
| `src-tauri/src/license/encrypted_store.rs` | Saves/loads license.enc with AES-256-GCM keyed by hardware ID. |
| `src-tauri/src/commands/license.rs` | Tauri commands: validate_license, get_license_status, activate_license, deactivate_license, get_hardware_id. |
| `src-tauri/src/license/registry.rs` | Fetches registry from REGISTRY_URL, verifies Ed25519 signature, checks revocation/expiry. |
| `license-generator/` | Python script to generate signed licenses and append to registry file (vendor only). |
| Frontend: `LicenseGate`, `LicenseInput`, `useLicense` | UI and activation flow; shows machine ID for vendor; no license secret, no trust. |

---

## How to Make It “More Secure” (Summary)

- **Keep one-machine binding:** Already in place via hardware_id + encrypted storage.
- **Harden hardware ID:** Done – hostname/CPU/OS normalized; add more stable identifiers (e.g. disk serial) if needed.
- **Protect HMAC secret:** Done – use `LICENSE_HMAC_SECRET` env var (≥ 32 chars) in production.
- **Add server activation (optional):** Server validates key/email, returns signed license; app only accepts that.
- **Re-validate periodically:** Frontend can call `validate_license` on a timer or window focus.
