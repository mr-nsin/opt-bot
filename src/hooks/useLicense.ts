import { useState, useCallback, useEffect } from "react";
import { license, trading } from "@/lib/tauri-commands";
import type { LicenseStatus } from "@/lib/types";

/** True if validate error indicates revocation, expiry, or no license. Do NOT fall back to local; stop trading. */
function isRevocationError(err: unknown): boolean {
  const msg = String(err ?? "").toLowerCase();
  return (
    msg.includes("not found") ||
    msg.includes("revoked") ||
    msg.includes("expired") ||
    msg.includes("registry check failed") ||
    msg.includes("license file not found")
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
          // Key removed from Drive: invalidate local, stop trading, show license gate
          try {
            await license.invalidateLicenseState();
          } catch {
            /* ignore */
          }
          try {
            await trading.emergencyStop();
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
          // Network/timeout: fall back to local (offline grace)
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

  // Proactive expiry check: if expires_at has passed, invalidate and stop trading within 60 sec
  useEffect(() => {
    if (!licenseStatus?.valid || !licenseStatus?.expires_at) return;
    const checkExpired = () => {
      try {
        const exp = new Date(licenseStatus!.expires_at!).getTime();
        if (Date.now() > exp) {
          license.invalidateLicenseState().catch(() => {});
          trading.emergencyStop().catch(() => {});
          setLicenseStatus((p) => (p ? { ...p, valid: false, error: "License has expired" } : p));
        }
      } catch {
        /* ignore parse errors */
      }
    };
    checkExpired(); // run immediately
    const id = setInterval(checkExpired, 60 * 1000); // then every 60 seconds
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
              await license.invalidateLicenseState();
            } catch {
              /* ignore */
            }
            try {
              await trading.emergencyStop();
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
          // Network/timeout: leave status as-is (offline grace)
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
