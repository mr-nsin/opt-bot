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
import { PnLSparkline } from "./PnLSparkline";
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
    <div className="space-y-2.5">
      {/* Live P&L Stats - always visible at top (compact row) */}
      <LiveStats />

      {/* Tab navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <BarChart3 className="h-3 w-3" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="signals">
            <Zap className="h-3 w-3" />
            Signals & Market
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings2 className="h-3 w-3" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="engine">
            <Radio className="h-3 w-3" />
            Engine
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="h-3 w-3" />
            Activity
          </TabsTrigger>
        </TabsList>

        {/* === Overview Tab — Chart-centric === */}
        <TabsContent value="overview">
          <div className="space-y-2">
            {/* Hero: P&L chart takes dominant space, controls tight on right */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-2">
              <div className="lg:col-span-4">
                <PnLSparkline />
              </div>
              <TradingControls />
            </div>

            {/* Account + Risk — wider account panel */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-2">
              <div className="lg:col-span-3">
                <AccountSummary />
              </div>
              <div className="lg:col-span-2">
                <RiskManagement />
              </div>
            </div>

            {/* Data Feed */}
            <DataFeedStatus />
          </div>
        </TabsContent>

        {/* === Signals & Market Tab === */}
        <TabsContent value="signals">
          <div className="space-y-2">
            <MarketOverview />
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-2">
              <div className="lg:col-span-3">
                <SignalActivity />
              </div>
              <div className="lg:col-span-2">
                <DataFeedStatus />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* === Configuration Tab === */}
        <TabsContent value="config">
          <div className="space-y-2">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
              <TradingControls />
              <TradeParameters />
              <RiskManagement />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
              <ConnectionConfig />
              <StockList />
            </div>
          </div>
        </TabsContent>

        {/* === Engine Tab === */}
        <TabsContent value="engine">
          <div className="space-y-2">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-2">
              <div className="lg:col-span-3">
                <EngineActivity />
              </div>
              <div className="lg:col-span-2">
                <SignalActivity />
              </div>
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
