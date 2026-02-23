import { LiveStats } from "./LiveStats";
import { AccountSummary } from "./AccountSummary";
import { DataFeedStatus } from "./DataFeedStatus";
import { TradingControls } from "./TradingControls";
import { TradeParameters } from "./TradeParameters";
import { RiskManagement } from "./RiskManagement";
import { ConnectionConfig } from "./ConnectionConfig";
import { StockList } from "./StockList";
import { ActivityLog } from "./ActivityLog";

export function DashboardPage() {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1">
        <LiveStats />
        <p className="text-2xs text-muted-foreground/80 px-0.5">
          Updates: PnL ~1s · Account summary ~5s · Data status ~10s
        </p>
      </div>

      <AccountSummary />

      <DataFeedStatus />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <TradingControls />
        <TradeParameters />
        <RiskManagement />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ConnectionConfig />
        <StockList />
      </div>

      <ActivityLog />
    </div>
  );
}
