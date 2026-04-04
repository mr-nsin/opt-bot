import { useState, useCallback, useEffect } from "react";
import { license, trading } from "@/lib/tauri-commands";
import type { LicenseStatus } from "@/lib/types";

/** True ONLY when the registry explicitly says the license was revoked or the key is missing.
 * Network failures, timeouts, and "file not found" are NOT revocations — never delete local license for those. */
function isRevocationError(err: unknown): boolean {
  const msg = String(err ?? "").toLowerCase();
  return (
    msg.includes("not found in registry") ||
    msg.includes("revoked")
  );
}

export function useLicense() {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkLicense = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true);
      setError(null);
    }
    const timeoutMs = 5000;
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("License check timed out")), timeoutMs)
    );
    try {
      const status = await Promise.race([license.validate(), timeoutPromise]);
      setLicenseStatus(status as LicenseStatus);
    } catch (err) {
      if (!opts?.silent) {
        if (isRevocationError(err)) {
          // Key was explicitly removed from the registry — stop trading and show license gate.
          // Do NOT delete license.enc: the user may re-subscribe, and keeping the local file
          // lets the system auto-recover on next validate without manual re-activation.
          try {
            await trading.emergencyStop(
              "License revoked — trading stopped"
            );
          } catch {
            /* ignore if sidecar not running */
          }
          setLicenseStatus({
            valid: false,
            tier: "",
            days_remaining: 0,
            expires_at: "",
            features: {
              live_trading: false,
              max_symbols: 0,
              max_daily_trades: 0,
              strategies: [],
            },
            hardware_bound: false,
            error: String(err),
          });
        } else {
          // Network/timeout/other: fall back to local validation (offline grace)
          try {
            const status = (await license.getStatus()) as LicenseStatus;
            setLicenseStatus(status);
            if (!status.valid) {
              try {
                await trading.emergencyStop();
              } catch {
                /* ignore */
              }
            }
          } catch {
            setLicenseStatus({
              valid: false,
              tier: "",
              days_remaining: 0,
              expires_at: "",
              features: {
                live_trading: false,
                max_symbols: 0,
                max_daily_trades: 0,
                strategies: [],
              },
              hardware_bound: false,
              error: String(err),
            });
          }
        }
      }
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, []);

  const activateLicense = useCallback(async (key: string, email: string) => {
    setLoading(true);
    setError(null);
    try {
      const status = await license.activate(key, email);
      setLicenseStatus(status);
      return status;
    } catch (err) {
      const msg = String(err);
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const deactivateLicense = useCallback(async () => {
    try {
      await license.deactivate();
      setLicenseStatus(null);
    } catch (err) {
      setError(String(err));
    }
  }, []);

  useEffect(() => {
    checkLicense();
  }, [checkLicense]);

  // Proactive expiry check: if expires_at has passed, mark invalid in UI and stop trading.
  // NEVER delete license.enc here — the user may just need to renew, and deleting forces
  // full re-activation instead of a simple registry refresh.
  useEffect(() => {
    if (!licenseStatus?.valid || !licenseStatus?.expires_at) return;
    const checkExpired = () => {
      try {
        const exp = new Date(licenseStatus!.expires_at!).getTime();
        if (Date.now() > exp) {
          trading.emergencyStop("License expired — trading stopped").catch(() => {});
          setLicenseStatus((p) => (p ? { ...p, valid: false, error: "License has expired" } : p));
        }
      } catch {
        /* ignore parse errors */
      }
    };
    checkExpired();
    const id = setInterval(checkExpired, 60 * 1000);
    return () => clearInterval(id);
  }, [licenseStatus?.valid, licenseStatus?.expires_at]);

  // Re-validate periodically against registry (Google Drive); first check at 1 min, then every 30 min
  useEffect(() => {
    const runValidate = () => {
      license
        .validate()
        .then((s) => setLicenseStatus(s as LicenseStatus))
        .catch(async (err) => {
          if (isRevocationError(err)) {
            try {
              await trading.emergencyStop(
                "License revoked — trading stopped"
              );
            } catch {
              /* ignore if sidecar not running */
            }
            setLicenseStatus((prev) =>
              prev
                ? { ...prev, valid: false, error: String(err) }
                : {
                    valid: false,
                    tier: "",
                    days_remaining: 0,
                    expires_at: "",
                    features: {
                      live_trading: false,
                      max_symbols: 0,
                      max_daily_trades: 0,
                      strategies: [],
                    },
                    hardware_bound: false,
                    error: String(err),
                  }
            );
          }
          // Network/timeout/other: leave status as-is (offline grace)
        });
    };
    const intervalMs = 30 * 60 * 1000; // 30 minutes
    const earlyCheckMs = 60 * 1000; // 1 minute - first follow-up check
    const earlyId = setTimeout(runValidate, earlyCheckMs);
    const intervalId = setInterval(runValidate, intervalMs);
    return () => {
      clearTimeout(earlyId);
      clearInterval(intervalId);
    };
  }, []);

  return {
    licenseStatus,
    isLicensed: licenseStatus?.valid ?? false,
    loading,
    error,
    checkLicense,
    activateLicense,
    deactivateLicense,
  };
}
