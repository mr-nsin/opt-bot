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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
            Analytics
          </h2>
          <p className="text-xs text-muted-foreground">Performance metrics and trade analysis</p>
        </div>
        {totalTrades > 0 && (
          <div className="text-xs text-muted-foreground/60">
            Based on {totalTrades} trade{totalTrades !== 1 ? "s" : ""} today
          </div>
        )}
      </div>

      {totalTrades === 0 && (
        <Alert variant="info">
          <AlertDescription>
            Start trading to see analytics. Metrics update in real-time as trades are executed.
          </AlertDescription>
        </Alert>
      )}

      {/* Performance metrics - always visible */}
      <PerformanceMetrics />

      {/* Chart tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <Activity className="h-3.5 w-3.5" />
            All Charts
          </TabsTrigger>
          <TabsTrigger value="pnl">
            <TrendingUp className="h-3.5 w-3.5" />
            P&L Analysis
          </TabsTrigger>
          <TabsTrigger value="distribution">
            <PieChart className="h-3.5 w-3.5" />
            Distribution
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <WinLossChart />
            <EquityCurve />
          </div>
          <div className="mt-4">
            <PnLChart />
          </div>
        </TabsContent>

        <TabsContent value="pnl">
          <div className="space-y-4">
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
