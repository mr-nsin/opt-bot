# License + Trading: Complete Analysis

**Last updated:** Mar 4, 2026

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                                   │
│  LicenseGate → useLicense → license.validate / getStatus / invalidate        │
│                         → trading.emergencyStop / start / stop              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TAURI (Rust)                                      │
│  app.licensed, app.license                                                   │
│  start_trading checks app.licensed before allowing start                      │
│  emergency_stop kills sidecar (no license check)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRADING ENGINE (Python sidecar)                           │
│  Separate process, spawned by Rust                                           │
│  Runs BOT logic: signals, orders, positions, TWS connection                  │
│  Killed by emergency_stop / stop_trading                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Validation Sources

| Source | When Used | What It Checks |
|--------|-----------|----------------|
| **Drive (Registry)** | Primary for `validate()` | Fetches JSON from REGISTRY_URL, finds entry by key+email, verifies Ed25519, hardware, expiry |
| **Local file** | Fallback for `getStatus()` when validate fails (network/timeout) | Loads `license.enc`, verifies HMAC, hardware, expiry. No registry contact. |

---

## 3. Startup Flow

```
App launch
    │
    ▼
LicenseGate mounts → useLicense
    │
    ▼
checkLicense() runs (once)
    │
    ├─► validate() ─► Drive registry
    │       │
    │       ├─ success ─► setLicenseStatus(valid) ─► show app
    │       │
    │       └─ fail (revocation/expiry/not found)
    │               │
    │               ├─ invalidateLicenseState()  (delete license.enc, app.licensed=false)
    │               ├─ emergencyStop()          (kill sidecar if running)
    │               └─ setLicenseStatus(valid: false) ─► show LicenseGate
    │
    └─ fail (network/timeout)
            │
            └─ getStatus() (local only)
                    │
                    ├─ valid ─► show app (offline grace)
                    │
                    └─ invalid ─► emergencyStop() + setLicenseStatus(invalid) ─► show LicenseGate
```

---

## 4. Periodic Checks (While App Running)

| Check | Interval | Action |
|-------|----------|--------|
| **Proactive expiry** | Every 60 sec | Compare `Date.now()` vs `expires_at`. If passed → invalidate + emergencyStop + show gate |
| **Registry re-validation** | 1 min after mount, then every 30 min | Call validate(). On revocation/expiry → invalidate + emergencyStop + show gate |
| **Network failure (periodic)** | N/A | Leave status as-is (offline grace). Do NOT invalidate |

---

## 5. License → Trading Coupling

### 5.1 Starting Trading

```
User clicks "Start Trading"
    │
    ▼
start_trading (Rust)
    │
    ├─ if !app.licensed ─► Err("Valid license required") ─► UI shows error
    │
    └─ else ─► Spawn sidecar (if needed) + send START_TRADING ─► trading runs
```

### 5.2 Stopping Trading When License Invalidates

| Trigger | Location | Action |
|---------|----------|--------|
| Revocation (key removed from Drive) | checkLicense catch / runValidate catch | `emergencyStop()` |
| Expiry (from registry) | validate() returns "License has expired" | `emergencyStop()` |
| Expiry (local `expires_at` passed) | Proactive 60s check | `emergencyStop()` |
| getStatus returns valid: false | checkLicense fallback | `emergencyStop()` |

### 5.3 emergency_stop vs stop_trading

| Command | License check | When to use |
|---------|---------------|-------------|
| `stop_trading` | None | User clicks "Stop Trading". Requires status=Running. |
| `emergency_stop` | None | License invalidated. Always runs (no status check). Kills sidecar. |

---

## 6. Timing: When License Gate Shows

| Scenario | Max wait until gate |
|----------|---------------------|
| **App closed, key removed** | Immediate on next launch |
| **App just opened, key removed right after startup** | 1 min (early check) |
| **App running, key removed** | 30 min (periodic check) |
| **License expires (expires_at passes)** | 60 sec (proactive check) |

---

## 7. Error Classification

### 7.1 Revocation-type (invalidate + stop trading)

- `"not found"` (e.g. "License not found in registry")
- `"revoked"`
- `"expired"`
- `"registry check failed"`
- `"license file not found"`

→ No fallback to local. Invalidate, emergencyStop, show gate.

### 7.2 Network/timeout (fallback to local)

- Timeout (5s)
- Connection refused
- DNS failure
- etc.

→ Fall back to `getStatus()`. If local valid: offline grace. If local invalid: emergencyStop + show gate.

---

## 8. State Transitions

```
                    ┌─────────────┐
                    │ No license  │
                    │ (gate)      │
                    └──────┬──────┘
                           │ activate(key, email) → Drive
                           ▼
                    ┌─────────────┐
                    │ Licensed    │
                    │ (app)       │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         │ validate fail   │ expires_at      │ deactivate
         │ (revoked)       │ passes          │ (user)
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Invalidate  │   │ Invalidate  │   │ Delete      │
    │ + Stop      │   │ + Stop      │   │ license     │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └─────────────────┴─────────────────┘
                             │
                             ▼
                    ┌─────────────┐
                    │ No license  │
                    │ (gate)      │
                    └─────────────┘
```

---

## 9. Trading Engine Lifecycle

| Event | Sidecar state |
|-------|---------------|
| App starts | Not running |
| User clicks Start Trading | Spawned (if needed), receives START_TRADING |
| License invalidates (any trigger) | emergencyStop → EMERGENCY_STOP → kill after 15s |
| User clicks Stop Trading | stop_trading → STOP_TRADING → kill after 3s |
| User clicks Emergency Stop | emergency_stop → EMERGENCY_STOP → kill after 15s |
| App exits | Process orphaned (may need OS cleanup) |

---

## 10. Edge Cases

| Case | Behavior |
|------|----------|
| Trading running, user goes offline | validate() fails (network). Fallback to getStatus. If local valid: stays licensed, trading continues. |
| Trading running, key removed while offline | validate() fails. Fallback getStatus: local still valid (not revoked). User stays licensed until back online. Next validate: not found → invalidate + stop. |
| License expires at midnight, user online | Proactive check (60s) detects at 00:01. Invalidate + emergencyStop. |
| License expires, user offline | validate fails (network). getStatus: local expired → valid: false. emergencyStop + show gate. |
| Sidecar crashes, license valid | UI shows disconnected. User can click Start again (app.licensed still true). |
| User activates, then key removed before first periodic check | At t=1min or t=30min, validate fails → invalidate + emergencyStop. |

---

## 11. Files Reference

| File | Role |
|------|------|
| `src/hooks/useLicense.ts` | checkLicense, periodic validate, proactive expiry, revocation handling, emergencyStop on invalid |
| `src/components/license/LicenseGate.tsx` | Renders gate or children based on isLicensed |
| `src-tauri/src/commands/license.rs` | validate_license, get_license_status, activate, deactivate, invalidate_license_state |
| `src-tauri/src/commands/trading.rs` | start_trading (checks license), stop_trading, emergency_stop |
| `src-tauri/src/license/` | validator, encrypted_store, registry, hardware_id |

---

## 12. Summary

- **Primary validation:** Drive registry. Local used only as fallback when network fails.
- **Trading blocked** when `app.licensed` is false (start_trading returns Err).
- **Trading stopped** when license invalidates (revocation, expiry, getStatus invalid) via `emergencyStop()`.
- **Max delay to gate:** 1 min (early check), 30 min (periodic), or 60 sec (expiry).
- **Offline:** User can continue if local license valid. Revocation not detected until back online.
