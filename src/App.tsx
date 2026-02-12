import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LicenseGate } from "@/components/license/LicenseGate";
import { DashboardPage } from "@/components/dashboard/DashboardPage";
import { AnalyticsPage } from "@/components/analytics/AnalyticsPage";
import { PositionsPage } from "@/components/positions/PositionsPage";
import { LogsPage } from "@/components/logs/LogsPage";
import { SettingsPage } from "@/components/settings/SettingsPage";
import { Toaster } from "@/components/common/Toaster";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useTheme } from "@/hooks/useTheme";
import { useTradingEvents } from "@/hooks/useTradingEvents";
import { config, logs as logsApi } from "@/lib/tauri-commands";

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
        const tradingConfig = await config.get();
        setTradingConfig(tradingConfig);
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

  // Apply font size setting to the document root
  useEffect(() => {
    document.documentElement.style.fontSize = `${settings.font_size}px`;
  }, [settings.font_size]);

  return (
    <>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
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
