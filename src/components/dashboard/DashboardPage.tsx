import { LiveStats } from "./LiveStats";
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
      <LiveStats />

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
