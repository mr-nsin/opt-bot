import { useState, memo } from "react";
import { PerformanceMetrics } from "./PerformanceMetrics";
import { WinLossChart } from "./WinLossChart";
import { PnLChart } from "./PnLChart";
import { EquityCurve } from "./EquityCurve";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useTradingStore } from "@/stores/tradingStore";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  BarChart3,
  TrendingUp,
  PieChart,
  Activity,
} from "lucide-react";

export const AnalyticsPage = memo(function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  const isRunning = useTradingStore((s) => s.status) === "Running";

  return (
    <div className="space-y-3">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary/80" />
            Analytics
          </h2>
          <p className="text-sm text-muted-foreground">Performance metrics and trade analysis</p>
        </div>
        {totalTrades > 0 && (
          <div className="text-sm text-muted-foreground font-mono tabular-nums">
            {openTrades} open / {closedTrades} closed ({totalTrades} total)
          </div>
        )}
      </div>

      {totalTrades === 0 && !isRunning && (
        <Alert variant="info">
          <AlertDescription>
            Start trading to see analytics. Metrics update in real-time as trades are executed.
          </AlertDescription>
        </Alert>
      )}

      <PerformanceMetrics />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <Activity className="h-3 w-3" />
            All Charts
          </TabsTrigger>
          <TabsTrigger value="pnl">
            <TrendingUp className="h-3 w-3" />
            P&L Analysis
          </TabsTrigger>
          <TabsTrigger value="distribution">
            <PieChart className="h-3 w-3" />
            Distribution
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
            <WinLossChart />
            <EquityCurve />
          </div>
          <div className="mt-2">
            <PnLChart />
          </div>
        </TabsContent>

        <TabsContent value="pnl">
          <div className="space-y-2">
            <EquityCurve />
            <PnLChart />
          </div>
        </TabsContent>

        <TabsContent value="distribution">
          <WinLossChart />
        </TabsContent>
      </Tabs>
    </div>
  );
});
