import { useState } from "react";
import { LiveStats } from "./LiveStats";
import { AccountSummary } from "./AccountSummary";
import { DataFeedStatus } from "./DataFeedStatus";
import { TradingControls } from "./TradingControls";
import { TradeParameters } from "./TradeParameters";
import { RiskManagement } from "./RiskManagement";
import { ConnectionConfig } from "./ConnectionConfig";
import { StockList } from "./StockList";
import { ActivityLog } from "./ActivityLog";
import { SignalActivity } from "./SignalActivity";
import { MarketOverview } from "./MarketOverview";
import { EngineActivity } from "./EngineActivity";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Settings2,
  BarChart3,
  Zap,
  Activity,
  Radio,
} from "lucide-react";

export function DashboardPage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="space-y-4">
      {/* Live P&L Stats - always visible at top */}
      <div className="flex flex-col gap-1">
        <LiveStats />
        <p className="text-2xs text-muted-foreground/60 px-0.5">
          Updates: PnL ~1s · Account summary ~5s · Data status ~10s
        </p>
      </div>

      {/* Tab navigation for dashboard sections */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <BarChart3 className="h-3.5 w-3.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="signals">
            <Zap className="h-3.5 w-3.5" />
            Signals & Market
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings2 className="h-3.5 w-3.5" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="engine">
            <Radio className="h-3.5 w-3.5" />
            Engine
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="h-3.5 w-3.5" />
            Activity
          </TabsTrigger>
        </TabsList>

        {/* === Overview Tab === */}
        <TabsContent value="overview">
          <div className="space-y-4">
            {/* Account + Controls row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <AccountSummary />
              </div>
              <TradingControls />
            </div>

            {/* Risk + Data Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <RiskManagement />
              <DataFeedStatus />
            </div>
          </div>
        </TabsContent>

        {/* === Signals & Market Tab === */}
        <TabsContent value="signals">
          <div className="space-y-4">
            {/* Market overview */}
            <MarketOverview />

            {/* Signal activity + Data feed side-by-side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <SignalActivity />
              <DataFeedStatus />
            </div>
          </div>
        </TabsContent>

        {/* === Configuration Tab === */}
        <TabsContent value="config">
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <TradingControls />
              <TradeParameters />
              <RiskManagement />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ConnectionConfig />
              <StockList />
            </div>
          </div>
        </TabsContent>

        {/* === Engine Tab — Signal scanner + order activity live feed === */}
        <TabsContent value="engine">
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <EngineActivity />
              <SignalActivity />
            </div>
            <DataFeedStatus />
          </div>
        </TabsContent>

        {/* === Activity Tab === */}
        <TabsContent value="activity">
          <ActivityLog />
        </TabsContent>
      </Tabs>
    </div>
  );
}
