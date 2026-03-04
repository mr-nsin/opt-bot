import { useState, useCallback, useEffect } from "react";
import { license } from "@/lib/tauri-commands";
import type { LicenseStatus } from "@/lib/types";

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
      setLicenseStatus(status);
    } catch (err) {
      if (!opts?.silent) {
        try {
          const status = await license.getStatus();
          setLicenseStatus(status as LicenseStatus);
        } catch {
          setLicenseStatus({ valid: false, tier: "", days_remaining: 0, expires_at: "", features: { live_trading: false, max_symbols: 0, max_daily_trades: 0, strategies: [] }, hardware_bound: false, error: String(err) });
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

  // Re-validate periodically against registry (Google Drive); when validity is updated there, UI will reflect it
  useEffect(() => {
    const runValidate = () => {
      license.validate().then(setLicenseStatus).catch(() => {});
    };
    // Check more frequently when near expiry (<=7 days) so vendor extension is picked up sooner
    const daysLeft = licenseStatus?.days_remaining ?? 999;
    const intervalMs =
      daysLeft <= 7 ? 30 * 60 * 1000 : 4 * 60 * 60 * 1000; // 30 min if expiring soon, else 4 hours
    const id = setInterval(runValidate, intervalMs);
    return () => clearInterval(id);
  }, [licenseStatus?.days_remaining]);

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
