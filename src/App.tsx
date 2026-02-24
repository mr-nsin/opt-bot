import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LicenseGate } from "@/components/license/LicenseGate";
import { Toaster } from "@/components/common/Toaster";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useTheme } from "@/hooks/useTheme";
import { useTradingEvents } from "@/hooks/useTradingEvents";
import { config, logs as logsApi } from "@/lib/tauri-commands";

const DashboardPage = lazy(() =>
  import("@/components/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const AnalyticsPage = lazy(() =>
  import("@/components/analytics/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage }))
);
const PositionsPage = lazy(() =>
  import("@/components/positions/PositionsPage").then((m) => ({ default: m.PositionsPage }))
);
const LogsPage = lazy(() =>
  import("@/components/logs/LogsPage").then((m) => ({ default: m.LogsPage }))
);
const SettingsPage = lazy(() =>
  import("@/components/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

function AppContent() {
  const { setTradingConfig, setSettings, settings } = useConfigStore();
  const { setLogs } = useLogStore();

  // Initialize theme
  useTheme();

  // Set up global trading event listeners (must be called once at root)
  useTradingEvents();

  // Load config, settings, and initial logs on mount
  useEffect(() => {
    const initialize = async () => {
      try {
        let tradingConfig = await config.get();
        const list = tradingConfig?.stock_list_to_trade || {};
        const symbols = Object.keys(list);
        const defaultFutures = { MNQU5: "CME", NQU5: "CME" };
        const defaultData = { MNQU5: { amount: 350 }, NQU5: { amount: 350 } };
        if (!symbols.length) {
          tradingConfig = {
            ...tradingConfig,
            stock_list_to_trade: { ...defaultFutures },
            stock_data: { ...(tradingConfig?.stock_data || {}), ...defaultData },
          };
          setTradingConfig(tradingConfig);
          await config.save(tradingConfig);
        } else {
          // Ensure both default futures (MNQU5, NQU5) are present when either is present
          const needNQU5 = list["MNQU5"] !== undefined && list["NQU5"] === undefined;
          const needMNQU5 = list["NQU5"] !== undefined && list["MNQU5"] === undefined;
          if (needNQU5 || needMNQU5) {
            const nextList = { ...list, ...(needNQU5 && { NQU5: "CME" }), ...(needMNQU5 && { MNQU5: "CME" }) };
            const nextData = { ...(tradingConfig?.stock_data || {}), ...(needNQU5 && { NQU5: { amount: 350 } }), ...(needMNQU5 && { MNQU5: { amount: 350 } }) };
            tradingConfig = { ...tradingConfig, stock_list_to_trade: nextList, stock_data: nextData };
            setTradingConfig(tradingConfig);
            await config.save(tradingConfig);
          } else {
            setTradingConfig(tradingConfig);
          }
        }
      } catch (err) {
        console.warn("Failed to load trading config, using defaults:", err);
      }

      try {
        const loadedSettings = await config.getSettings();
        setSettings(loadedSettings);
      } catch (err) {
        console.warn("Failed to load settings, using defaults:", err);
      }

      // Load initial logs from the Rust buffer
      try {
        const initialLogs = await logsApi.get(undefined, undefined, 200);
        if (initialLogs.length > 0) {
          setLogs(initialLogs);
        }
      } catch (err) {
        console.warn("Failed to load initial logs:", err);
      }
    };

    initialize();
  }, [setTradingConfig, setSettings, setLogs]);

  // Apply font size setting to the document root (clamp so UI never looks too small or large)
  useEffect(() => {
    const size = Math.max(12, Math.min(24, settings.font_size));
    document.documentElement.style.fontSize = `${size}px`;
  }, [settings.font_size]);

  return (
    <>
      <Suspense
        fallback={
          <div className="flex h-screen w-full items-center justify-center bg-background">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              </div>
              <p className="text-sm text-muted-foreground">Loading…</p>
            </div>
          </div>
        }
      >
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/positions" element={<PositionsPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </Suspense>
      <Toaster />
    </>
  );
}

export default function App() {
  return (
    <LicenseGate>
      <AppContent />
    </LicenseGate>
  );
}
