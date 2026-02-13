import { useState, useCallback, useEffect } from "react";
import { license } from "@/lib/tauri-commands";
import type { LicenseStatus } from "@/lib/types";

export function useLicense() {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkLicense = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await license.validate();
      setLicenseStatus(status);
    } catch (err) {
      // Try getting status instead (might be expired or not found)
      try {
        const status = await license.getStatus();
        setLicenseStatus(status as LicenseStatus);
      } catch {
        setLicenseStatus({ valid: false, tier: "", days_remaining: 0, expires_at: "", features: { live_trading: false, max_symbols: 0, max_daily_trades: 0, strategies: [] }, hardware_bound: false, error: String(err) });
      }
    } finally {
      setLoading(false);
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

  // Re-validate periodically against registry (revocation / expiry)
  useEffect(() => {
    const intervalMs = 4 * 60 * 60 * 1000; // 4 hours
    const id = setInterval(() => {
      license.validate().then(setLicenseStatus).catch(() => {});
    }, intervalMs);
    return () => clearInterval(id);
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
