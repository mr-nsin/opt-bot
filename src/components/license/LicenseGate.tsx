import { useState, useEffect } from "react";
import { Activity, Loader2, Cpu, Copy, Check } from "lucide-react";
import { LicenseInput } from "./LicenseInput";
import { LicenseStatus } from "./LicenseStatus";
import { useLicense } from "@/hooks/useLicense";
import { license as licenseApi } from "@/lib/tauri-commands";

/** Set to true to skip license check and always show the app. Set back to false to re-enable license gate. */
const SKIP_LICENSE_CHECK = true;

interface LicenseGateProps {
  children: React.ReactNode;
}

export function LicenseGate({ children }: LicenseGateProps) {
  const { isLicensed, licenseStatus, loading, error, activateLicense } = useLicense();
  const [hardwareId, setHardwareId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isLicensed && !loading) {
      licenseApi.getHardwareId().then(setHardwareId).catch(() => setHardwareId(null));
    }
  }, [isLicensed, loading]);

  const copyHardwareId = () => {
    if (hardwareId) {
      navigator.clipboard.writeText(hardwareId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (SKIP_LICENSE_CHECK) return <>{children}</>;

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">Validating license...</p>
        </div>
      </div>
    );
  }

  if (isLicensed) return <>{children}</>;

  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2.5 mb-3">
            <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">QuantDrift</h1>
          </div>
          <p className="text-sm text-muted-foreground">Professional Options Trading Bot</p>
        </div>

        <div className="rounded-xl border bg-card p-6 shadow-card">
          <h2 className="text-sm font-semibold mb-4">Activate License</h2>
          <LicenseInput onActivate={activateLicense} error={error} />
          {licenseStatus && !licenseStatus.valid && (
            <div className="mt-4"><LicenseStatus status={licenseStatus} /></div>
          )}
          {hardwareId && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-2xs text-muted-foreground flex items-center gap-1.5 mb-1.5">
                <Cpu className="h-3 w-3" /> Your machine ID (send to vendor for a new license)
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-2xs font-mono bg-muted/50 rounded px-2 py-1.5 truncate" title={hardwareId}>
                  {hardwareId}
                </code>
                <button
                  type="button"
                  onClick={copyHardwareId}
                  className="shrink-0 p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                  title="Copy"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="text-center text-2xs text-muted-foreground mt-6">
          Need help?{" "}
          <a href="mailto:support@quantdrift.com" className="text-primary hover:underline">support@quantdrift.com</a>
        </p>
      </div>
    </div>
  );
}
