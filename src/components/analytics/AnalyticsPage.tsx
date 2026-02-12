import { PerformanceMetrics } from "./PerformanceMetrics";
import { WinLossChart } from "./WinLossChart";
import { PnLChart } from "./PnLChart";
import { EquityCurve } from "./EquityCurve";

export function AnalyticsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Analytics</h2>
        <p className="text-xs text-muted-foreground">Performance metrics and trade analysis</p>
      </div>
      <PerformanceMetrics />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WinLossChart />
        <EquityCurve />
      </div>
      <PnLChart />
    </div>
  );
}
