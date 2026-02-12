import { Activity, Loader2 } from "lucide-react";
import { LicenseInput } from "./LicenseInput";
import { LicenseStatus } from "./LicenseStatus";
import { useLicense } from "@/hooks/useLicense";

interface LicenseGateProps {
  children: React.ReactNode;
}

export function LicenseGate({ children }: LicenseGateProps) {
  const { isLicensed, licenseStatus, loading, error, activateLicense } = useLicense();

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
        </div>

        <p className="text-center text-2xs text-muted-foreground mt-6">
          Need help?{" "}
          <a href="mailto:support@quantdrift.com" className="text-primary hover:underline">support@quantdrift.com</a>
        </p>
      </div>
    </div>
  );
}
