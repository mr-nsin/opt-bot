import type { LicenseStatus as LicenseStatusType } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Shield, ShieldAlert, Clock, Star } from "lucide-react";

export function LicenseStatus({ status }: { status: LicenseStatusType }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {status.valid ? <Shield className="h-4 w-4 text-emerald-500" /> : <ShieldAlert className="h-4 w-4 text-red-500" />}
        <Badge variant={status.valid ? "success" : "danger"}>{status.valid ? "Active" : "Inactive"}</Badge>
        {status.tier && <Badge variant="secondary" className="capitalize gap-1"><Star className="h-3 w-3" />{status.tier}</Badge>}
      </div>
      {status.valid && (
        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
          <Clock className="h-3 w-3" />
          <span className="font-medium tabular-nums">{status.days_remaining} days left</span>
          {status.days_remaining <= 7 && <span className="text-amber-500 font-medium">(expiring soon)</span>}
        </div>
      )}
      {status.error && <p className="text-xs text-red-500 bg-red-500/10 rounded-md p-2 border border-red-500/20">{status.error}</p>}
    </div>
  );
}
