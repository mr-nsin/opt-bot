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
import { SignalDataTable } from "./SignalDataTable";
import { MarketOverview } from "./MarketOverview";
import { EngineActivity } from "./EngineActivity";
import { PnLSparkline } from "./PnLSparkline";
import { StockPricesGrid } from "./StockPricesGrid";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useTradingEngine } from "@/hooks/useTradingEngine";
import { useConfigStore } from "@/stores/configStore";
import { useNotificationStore } from "@/stores/notificationStore";
import { config as configApi } from "@/lib/tauri-commands";
import {
  Settings2,
  BarChart3,
  Zap,
  Activity,
  Save,
  Loader2,
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
  const { isIdle } = useTradingEngine();
  const tradingConfig = useConfigStore((s) => s.tradingConfig);
  const addToast = useNotificationStore((s) => s.addToast);
  const [saving, setSaving] = useState(false);
  const configDisabled = !isIdle;

  const handleSaveConfig = useCallback(async () => {
    if (!tradingConfig || configDisabled) return;
    setSaving(true);
    try {
      await configApi.save(tradingConfig);
      addToast({ title: "Configuration saved", message: "Trading config persisted to config.json", type: "success" });
    } catch (e) {
      addToast({ title: "Save failed", message: String(e), type: "error" });
    } finally {
      setSaving(false);
    }
  }, [tradingConfig, configDisabled, addToast]);

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
            <SignalDataTable />
          </div>
        </TabsContent>

        <TabsContent value="config">
          <div className="space-y-3 mt-3">
            {configDisabled && (
              <p className="text-xs text-amber-500 bg-amber-500/10 rounded-lg px-3 py-2 border border-amber-500/20">
                Configuration is locked while trading is running. Stop trading to edit and save.
              </p>
            )}
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={handleSaveConfig}
                disabled={configDisabled || !tradingConfig || saving}
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {saving ? "Saving…" : "Save Configuration"}
              </Button>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <TradeParameters disabled={configDisabled} />
              <RiskManagement disabled={configDisabled} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <ConnectionConfig disabled={configDisabled} />
              <StockList disabled={configDisabled} />
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
