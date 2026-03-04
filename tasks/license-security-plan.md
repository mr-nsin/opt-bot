# License Security Fixes — Implementation Plan

## Executive Summary: License Screen on Expiry

| When | Current Behavior | After Fixes |
|------|------------------|-------------|
| **App restart after expiry** | Yes — license screen shows | Yes |
| **Expiry while app is running** | No — user stays "licensed" until restart | Yes — within ~1 min via proactive expiry check |
| **Registry revoked while running** | No — stays licensed until restart | Yes — next periodic validate (or on next validate failure with "not found") |

**Validation source:** Primary path uses **Drive/registry**; fallback uses **local file only** (no revocation visibility when offline).

---

## 1. Current Validation Flow Analysis

### 1.1 What Gets Checked, When

| Check Point | Uses Local File | Uses Registry (Drive) | When |
|-------------|-----------------|------------------------|------|
| **Startup** (`checkLicense`) | Yes (load to get key+email) | Yes (fetch, verify, expiry) | Once on app launch |
| **Fallback** (when validate fails) | Yes | No | If network/timeout fails |
| **Periodic re-validation** | No (validate loads local first, then registry) | Yes | Every 4 hours |
| **get_license_status** | Yes | No | Fallback only; local validation |

### 1.2 Validation Source of Truth

- **Primary path** (`validate_license`): Always uses registry. Loads local file only to get `license_key` and `email` for registry lookup, then validates against registry entry (Ed25519, hardware, expiry).
- **Secondary path** (`get_license_status`): Uses local file only. No registry contact. Checks HMAC, hardware, expiry.

### 1.3 Expiry / Revocation — When Does License Screen Show?

| Scenario | Shows License Screen? |
|----------|------------------------|
| License expires **at startup** (cold start) | Yes — validate fails → catch → get_status returns `valid: false` (local file has same expires_at) |
| License expires **while app running** | No — next 4‑hour validate() fails, `.catch(() => {})` swallows error, `setLicenseStatus` never called, UI stays "licensed" |
| License revoked in registry **at startup** | Yes — validate fails (entry not found) → get_status: local file still exists, validator checks expiry/hardware but NOT revocation; if not expired, returns `valid: true` — revocation not applied until next successful validate |
| License revoked **while app running** | No — same as expiry; periodic validate fails, error ignored |

### 1.4 Gaps Identified

1. **Periodic re-validation ignores failures** — When `validate()` fails (expired, revoked, network), the error is swallowed; `licenseStatus` is never updated to invalid.
2. **Fallback can show "licensed" when revoked** — `get_license_status` only checks local file; it does not know about registry revocation.
3. **Expiry while app is open** — User can keep using for hours/days until they restart.
4. **No proactive expiry check** — No timer that checks `expires_at` against current time; only the 4‑hour registry call would catch it (and that currently fails to update UI).

---

## 2. Implementation Plan

### Phase 1: Critical Security Fixes

#### 1.1 Remove / Harden `SKIP_LICENSE_CHECK`

**File:** `src/components/license/LicenseGate.tsx`

| Option | Approach |
|--------|----------|
| A (Recommended) | Remove the constant. Always enforce license gate. Use `import.meta.env.DEV` only for local dev (if needed). |
| B | Use build-time env: `VITE_SKIP_LICENSE=false` in production, `true` only in dev scripts. Strip from prod build. |

**Action:** Remove `SKIP_LICENSE_CHECK` and the conditional bypass. License gate always active in shipped builds.

- [ ] Remove `SKIP_LICENSE_CHECK` constant
- [ ] Remove `if (SKIP_LICENSE_CHECK) return <>{children}/>` branch
- [ ] Ensure `npm run build` produces no license bypass

---

#### 1.2 Fix Periodic Re-Validation to Update on Failure

**File:** `src/hooks/useLicense.ts`

**Current:**
```ts
license.validate().then(setLicenseStatus).catch(() => {});
```

**Problem:** On failure, status is never set to invalid.

**Action:** On failure, fetch status from backend (which will reflect invalid/expired) and update UI. If that fails too, force invalid.

- [ ] Change periodic effect to:
  - On success: `setLicenseStatus(status)`
  - On failure: Parse error message. If "not found in registry" or "revoked" → treat as revoked: call `invalidate_license_state()`, set `valid: false`, show license screen. Do NOT fall back to getStatus (would return valid from stale local file).
  - On failure: If network/timeout → fall back to `getStatus()`. If getStatus returns `valid: false` (e.g. expired), call `invalidate_license_state()` and set status. If getStatus returns `valid: true`, keep current status (offline grace).
- [ ] On `valid: false` from getStatus, also update backend `app.licensed` — requires new Tauri command or ensure Rust state is updated when we explicitly invalidate. **Note:** `get_license_status` does not update `app.licensed`. We need either:
  - A new command `revoke_license_locally` that clears app state when we detect invalid, or
  - Rely on the fact that on next `start_trading`, `app.licensed` is checked — but `app.licensed` stays true until validate succeeds or deactivate is called. So trading would still work!
  - **Must add:** When periodic check returns invalid, we need to clear `app.licensed` in Rust. Add command `set_license_revoked` or have `get_license_status` when returning invalid also update app state. Simpler: add `invalidate_license_state` command that sets `app.licensed = false` and `app.license = None`. Frontend calls it when we detect invalid from getStatus.

- [ ] Add Tauri command `invalidate_license_state` that sets `app.licensed = false`, `app.license = None` in Rust
- [ ] Call it from frontend when periodic validate fails and getStatus returns valid: false

---

#### 1.3 Add `simulate_demo` License Check

**File:** `src-tauri/src/commands/trading.rs`

- [ ] Add at start of `simulate_demo`:
  ```rust
  let app = state.lock().await;
  if !app.licensed {
      return Err("Valid license required to run demo".into());
  }
  ```
- [ ] Match the pattern used in `start_trading`

---

#### 1.4 HMAC Secret — Production Safety

**File:** `src-tauri/src/license/validator.rs`

- [ ] For release builds: require `LICENSE_HMAC_SECRET` (no default) or use `cfg!(debug_assertions)` to only use default in dev
- [ ] In production (`cfg!(not(debug_assertions))`): if `LICENSE_HMAC_SECRET` is empty or < 32 chars, refuse to sign/verify local licenses (or log warning and fail validation)
- [ ] Document in CLAUDE.md / README: set `LICENSE_HMAC_SECRET` when building/running production

---

### Phase 2: Expiry and Revocation UX

#### 2.1 Proactive Expiry Timer

**File:** `src/hooks/useLicense.ts`

Add a check that runs more frequently (e.g. every 5–15 minutes) that compares `licenseStatus.expires_at` with current time. If expired, set `licenseStatus` to invalid without waiting for registry.

- [ ] Add `useEffect` that:
  - If `licenseStatus?.valid && licenseStatus?.expires_at`:
  - Parse `expires_at` and check `now > expiry`
  - If expired, call `setLicenseStatus({ ...licenseStatus, valid: false, error: "License has expired" })` and `invalidate_license_state` (new command)
- [ ] Run every 60 seconds (or 5 min) as a lightweight check

---

#### 2.2 Startup checkLicense — Revocation Handling

**File:** `src/hooks/useLicense.ts`

When `validate()` fails, the catch block currently always falls back to `getStatus()`. For revocation ("not found in registry"), we must NOT use getStatus — local file would still say valid.

- [ ] In catch block: check error message. If contains "not found" or "revoked" → call `invalidate_license_state()`, set `licenseStatus` to `{ valid: false, error: msg }`, do NOT call getStatus.
- [ ] For other errors (network, timeout): call getStatus as today.

---

#### 2.3 Fallback Behavior When Offline

**Current:** When `validate()` fails, we call `get_license_status()`. If local file is valid (not expired, correct hardware), we show as licensed.

**Issue:** Registry revocation is not seen when offline.

**Options:**
- A) **Grace period:** When offline, allow N hours (e.g. 24–72) of cached validity, then require online check. Store `last_successful_registry_check` timestamp.
- B) **Strict:** Never trust local-only. When validate fails (including network), show as unlicensed after short grace (e.g. 5 min).
- C) **Keep current for now:** Accept that offline users with valid local file stay "licensed" until next successful validate. Document as known limitation.

**Recommendation:** Option C for now (minimal change). Add Phase 2.1 so at least expiry is enforced locally in near real-time.

---

### Phase 3: Backend State Sync on Invalidation

#### 3.1 New Tauri Command: `invalidate_license_state`

**File:** `src-tauri/src/commands/license.rs`

- [ ] Add `invalidate_license_state` command that:
  - Sets `app.license = None`
  - Sets `app.licensed = false`
  - Does NOT delete license.enc (user can retry when online)
- [ ] Register in `lib.rs`
- [ ] Expose in `tauri-commands.ts`
- [ ] Call from frontend when:
  - Periodic validate fails and getStatus returns `valid: false`
  - Proactive expiry check detects expired

---

### Phase 4: Documentation and Cleanup

- [ ] Update `docs/LICENSE_SYSTEM.md` with correct validation flow (local vs registry)
- [ ] Fix `docs/LICENSE_SETUP_STEPS.md` — remove "local-only mode" claim (code always uses registry defaults)
- [ ] Add `LICENSE_HMAC_SECRET` to production run instructions
- [ ] Update `CLAUDE.md` if needed

---

## 3. Summary Checklist

| # | Task | Priority |
|---|------|----------|
| 1 | Remove `SKIP_LICENSE_CHECK` bypass | High |
| 2 | Add `invalidate_license_state` Tauri command | High |
| 3 | Fix periodic re-validation: on failure, handle revocation vs offline | High |
| 4 | Fix startup checkLicense: on "not found" error, invalidate (no getStatus fallback) | High |
| 5 | Add proactive expiry timer (check every 60s) | High |
| 6 | Add license check to `simulate_demo` | Medium |
| 7 | Require/use `LICENSE_HMAC_SECRET` for production | Medium |
| 8 | Update docs | Low |

---

## 4. Validation Flow After Changes

| Event | Behavior |
|-------|----------|
| Startup, online | validate() → registry → if valid, show app |
| Startup, offline | validate() fails → getStatus() → local check → show app if not expired; else activation screen |
| Startup, expired | validate() fails → getStatus() → expired → activation screen |
| Running, expiry passes | Proactive timer (every 60s) detects expired → invalidate → activation screen |
| Running, 4h periodic | validate() → if fails, getStatus() → if invalid, invalidate → activation screen |
| Revoked in registry, next validate | validate() fails (entry not found) → getStatus() may still return valid from local → need to ensure we invalidate when validate fails and getStatus says invalid. For revocation, validate fails with "not found" — we then call getStatus. getStatus uses local file. The local license is NOT revoked — we'd get valid: true. So we need: when validate fails, we should NOT trust getStatus for revocation. We need to treat validate failure as "must re-validate when online" — so we could invalidate whenever validate fails (strict). That would break offline grace. |
| Revoked + offline | If we invalidate on validate failure, we'd lock out offline users. So: when validate fails, only invalidate if getStatus returns valid: false. If getStatus returns valid: true (local file still valid), allow continued use (offline grace). When they come back online, next validate will fail (revoked) and we won't find entry — validate returns Err. Then we call getStatus — local still has old data. We'd get valid: true. So we'd stay "licensed" until... we need getStatus to NOT return valid when we know the registry said revoked. We don't have that — getStatus doesn't hit registry. |
| Revocation fix | Option: when validate fails with "not found in registry", treat as revoked — invalidate immediately. Don't fall back to getStatus for that specific error. So: catch(err) { if (err.message?.includes('revoked') || err.message?.includes('not found')) { invalidate_license_state(); setLicenseStatus({ valid: false, error: err }); } else { getStatus()... } } |

**Revised revocation handling:**
- `validate()` fails with "License not found in registry (revoked or invalid)" → Treat as revoked. Call `invalidate_license_state`, set `valid: false`. Do not fall back to getStatus.
- `validate()` fails with network/timeout → Fall back to getStatus (offline grace).
- `validate()` fails with "License has expired" → invalidate, set valid: false.
- `get_license_status` returns valid: false (e.g. expired locally) → invalidate.

---

## 5. Answer: Will App Show License Screen When License Expires?

**Currently:**
- **On restart:** Yes. validate fails → get_status returns expired → license screen.
- **While running:** No. Periodic validate fails, error swallowed, UI not updated. User stays "licensed" until restart.

**After fixes:**
- **On restart:** Yes (unchanged).
- **While running:** Yes. Proactive 60s expiry check and fixed periodic re-validation will update `licenseStatus` to invalid and call `invalidate_license_state`, so LicenseGate will show the activation screen within about 1 minute of expiry (or when the next periodic check runs and detects revocation).
