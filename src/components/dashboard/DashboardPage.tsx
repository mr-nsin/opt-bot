import { useState, memo, useCallback } from "react";
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
import { StockPricesGrid } from "./StockPricesGrid";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Settings2,
  BarChart3,
  Zap,
  Activity,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const ACTIVITY_VIEWS = ["trading", "all"] as const;
type ActivityView = (typeof ACTIVITY_VIEWS)[number];

function ActivityTabContent() {
  const [view, setView] = useState<ActivityView>("trading");
  return (
    <div className="space-y-3 mt-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-muted-foreground">Show:</span>
        {ACTIVITY_VIEWS.map((v) => (
          <Button
            key={v}
            variant={view === v ? "default" : "outline"}
            size="sm"
            onClick={() => setView(v)}
          >
            {v === "trading" ? "Trading only" : "All logs"}
          </Button>
        ))}
      </div>
      {view === "trading" ? <EngineActivity /> : <ActivityLog />}
    </div>
  );
}

function DashboardPageInner() {
  const [activeTab, setActiveTab] = useState("overview");
  const setTab = useCallback((v: string) => setActiveTab(v), []);

  return (
    <div className="space-y-3">
      <LiveStats />

      <Tabs value={activeTab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <BarChart3 className="h-4 w-4 shrink-0" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="signals">
            <Zap className="h-4 w-4 shrink-0" />
            Signals & Market
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings2 className="h-4 w-4 shrink-0" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="h-4 w-4 shrink-0" />
            Activity
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="space-y-3 mt-3">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
              <div className="lg:col-span-4 min-h-0">
                <PnLSparkline />
              </div>
              <TradingControls />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 items-stretch">
              <div className="lg:col-span-3 min-w-0 flex flex-col">
                <AccountSummary />
              </div>
              <div className="lg:col-span-2 min-w-0 flex flex-col">
                <DataFeedStatus />
              </div>
            </div>

            <StockPricesGrid />
          </div>
        </TabsContent>

        <TabsContent value="signals">
          <div className="space-y-3 mt-3">
            <MarketOverview />
            <SignalActivity />
          </div>
        </TabsContent>

        <TabsContent value="config">
          <div className="space-y-3 mt-3">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <TradeParameters />
              <RiskManagement />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <ConnectionConfig />
              <StockList />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="activity">
          <ActivityTabContent />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const DashboardPage = memo(DashboardPageInner);
