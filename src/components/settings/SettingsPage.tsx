import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useConfigStore } from "@/stores/configStore";
import { useTheme } from "@/hooks/useTheme";
import { useLicense } from "@/hooks/useLicense";
import { config as configApi, trading as tradingApi, license as licenseApi } from "@/lib/tauri-commands";
import { useTauriEvent } from "@/hooks/useTauri";
import {
  Save,
  Moon,
  Sun,
  Shield,
  Bell,
  Palette,
  Zap,
  Check,
  LayoutGrid,
  FileJson,
  Keyboard,
  Monitor,
  FlaskConical,
  Cpu,
  Copy,
  RefreshCw,
} from "lucide-react";
import { LicenseStatus } from "@/components/license/LicenseStatus";
import { LicenseInput } from "@/components/license/LicenseInput";
import { formatHotkey } from "@/hooks/useHotkeys";
import { cn } from "@/lib/utils";

/** Keyboard shortcuts reference */
const SHORTCUTS = [
  { keys: formatHotkey("1"), action: "Go to Dashboard" },
  { keys: formatHotkey("2"), action: "Go to Analytics" },
  { keys: formatHotkey("3"), action: "Go to Positions" },
  { keys: formatHotkey("4"), action: "Go to Logs" },
  { keys: formatHotkey("5"), action: "Go to Settings" },
  { keys: formatHotkey("K"), action: "Command Palette" },
  { keys: "Esc", action: "Close overlay / dialog" },
];

export function SettingsPage() {
  const { settings, updateSettings, tradingConfig } = useConfigStore();
  const { isDark, toggleTheme } = useTheme();
  const { licenseStatus, isLicensed, activateLicense, checkLicense } = useLicense();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [settingsFile, setSettingsFile] = useState<Record<string, unknown> | null>(null);
  const [licenseInfo, setLicenseInfo] = useState<{ email: string; license_key: string } | null>(null);
  const [activeTab, setActiveTab] = useState("general");
  const [hardwareId, setHardwareId] = useState<string | null>(null);
  const [hwIdCopied, setHwIdCopied] = useState(false);
  const [refreshingLicense, setRefreshingLicense] = useState(false);

  useEffect(() => {
    configApi.getSettingsFile().then(setSettingsFile).catch(() => setSettingsFile(null));
  }, []);

  useEffect(() => {
    if (isLicensed) {
      licenseApi.getLicenseInfo().then((info) => setLicenseInfo(info ?? null)).catch(() => setLicenseInfo(null));
    } else {
      setLicenseInfo(null);
    }
  }, [isLicensed]);

  // Fetch hardware ID and refresh validity when License tab is active (show HW ID even when licensed)
  useEffect(() => {
    if (activeTab === "license") {
      licenseApi.getHardwareId().then(setHardwareId).catch(() => setHardwareId(null));
      // Re-validate silently when tab opened so updated expiry from vendor (Google Drive) is reflected
      checkLicense({ silent: true });
    }
  }, [activeTab, checkLicense]);

  const copyHardwareId = () => {
    if (hardwareId) {
      navigator.clipboard.writeText(hardwareId);
      setHwIdCopied(true);
      setTimeout(() => setHwIdCopied(false), 2000);
    }
  };

  const handleRefreshValidity = async () => {
    setRefreshingLicense(true);
    try {
      await checkLicense(); // Full check with loading state
    } finally {
      setRefreshingLicense(false);
    }
  };

  const handleSave = async () => {
    if (!tradingConfig) return;
    setSaving(true);
    try {
      await configApi.save(tradingConfig);
      await configApi.saveSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-2.5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Monitor className="h-5 w-5 text-primary/80" />
            Settings
          </h2>
          <p className="text-sm text-muted-foreground/70">Application preferences and configuration</p>
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving} className="h-8 text-xs">
          {saved ? <><Check className="h-3 w-3" /> Saved</> : <><Save className="h-3 w-3" /> {saving ? "Saving…" : "Save All"}</>}
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="general">
            <Palette className="h-3.5 w-3.5" />
            General
          </TabsTrigger>
          <TabsTrigger value="trading">
            <Zap className="h-3.5 w-3.5" />
            Trading
          </TabsTrigger>
          <TabsTrigger value="shortcuts">
            <Keyboard className="h-3.5 w-3.5" />
            Shortcuts
          </TabsTrigger>
          <TabsTrigger value="license">
            <Shield className="h-3.5 w-3.5" />
            License
          </TabsTrigger>
        </TabsList>

        {/* === General Tab === */}
        <TabsContent value="general">
          <div className="space-y-3">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2"><Palette className="h-4 w-4 text-violet-500" /> Appearance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <SettingRow
                  label="Dark Mode"
                  description="Toggle dark/light theme"
                  icon={isDark ? <Moon className="h-4 w-4 text-blue-400" /> : <Sun className="h-4 w-4 text-amber-500" />}
                >
                  <Switch checked={isDark} onCheckedChange={toggleTheme} />
                </SettingRow>
                <Separator />
                <SettingRow
                  label="Font Size (px)"
                  description="Base UI font size (12-24)"
                  icon={<LayoutGrid className="h-4 w-4 text-muted-foreground" />}
                >
                  <Input
                    type="number"
                    className="w-20 h-8 text-xs"
                    value={settings.font_size ?? 16}
                    onChange={(e) => updateSettings({ font_size: parseInt(e.target.value, 10) || 16 })}
                  />
                </SettingRow>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2"><Bell className="h-4 w-4 text-blue-500" /> Notifications</CardTitle>
              </CardHeader>
              <CardContent>
                <SettingRow
                  label="Show Notifications"
                  description="Trade alerts and system events"
                  icon={<Bell className="h-4 w-4 text-blue-500/70" />}
                >
                  <Switch checked={settings.show_notifications} onCheckedChange={(c) => updateSettings({ show_notifications: c })} />
                </SettingRow>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2"><LayoutGrid className="h-4 w-4 text-amber-500" /> UI Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <SettingRow
                  label="Update Interval (ms)"
                  description="Refresh rate for live data"
                  icon={<LayoutGrid className="h-4 w-4 text-muted-foreground" />}
                >
                  <Input
                    type="number"
                    className="w-24 h-8 text-xs"
                    value={settings.update_interval ?? 1000}
                    onChange={(e) => updateSettings({ update_interval: parseInt(e.target.value, 10) || 1000 })}
                  />
                </SettingRow>
                <Separator />
                <SettingRow
                  label="Show Charts"
                  description="Analytics and P&L charts"
                  icon={<LayoutGrid className="h-4 w-4 text-muted-foreground" />}
                >
                  <Switch checked={settings.show_charts ?? true} onCheckedChange={(c) => updateSettings({ show_charts: c })} />
                </SettingRow>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* === Trading Tab === */}
        <TabsContent value="trading">
          <div className="space-y-3">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2"><Zap className="h-4 w-4 text-amber-500" /> Trading Mode</CardTitle>
              </CardHeader>
              <CardContent>
                <SettingRow
                  label="Live Trading"
                  description="Enable real order execution (CAUTION: Real money at risk)"
                  icon={<Zap className="h-4 w-4 text-amber-500" />}
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={settings.trading_mode === "live" ? "danger" : "secondary"} className="text-2xs">
                      {settings.trading_mode.toUpperCase()}
                    </Badge>
                    <Switch
                      checked={settings.trading_mode === "live"}
                      onCheckedChange={(c) => updateSettings({ trading_mode: c ? "live" : "demo" })}
                    />
                  </div>
                </SettingRow>
              </CardContent>
            </Card>

            <DemoTestCard />

            {settingsFile && typeof settingsFile === "object" && (
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm flex items-center gap-2"><FileJson className="h-4 w-4 text-amber-500" /> config.json</CardTitle>
                  <CardDescription className="text-2xs">Single source: ui and trading</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  {(settingsFile as Record<string, unknown>).ui && typeof (settingsFile as Record<string, unknown>).ui === "object" && (
                    <ConfigSection title="UI" data={(settingsFile as Record<string, unknown>).ui as Record<string, unknown>} />
                  )}
                  {(settingsFile as Record<string, unknown>).stockListToTrade && (
                    <ConfigSection title="Symbols" data={{ stockListToTrade: (settingsFile as Record<string, unknown>).stockListToTrade }} />
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* === Shortcuts Tab === */}
        <TabsContent value="shortcuts">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Keyboard className="h-4 w-4 text-primary" />
                Keyboard Shortcuts
              </CardTitle>
              <CardDescription className="text-2xs">Navigate faster with keyboard shortcuts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {SHORTCUTS.map(({ keys, action }) => (
                  <div
                    key={keys}
                    className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-muted/30 transition-colors"
                  >
                    <span className="text-xs text-foreground/80">{action}</span>
                    <kbd className="px-2 py-0.5 rounded bg-muted border border-border/50 font-mono text-2xs text-muted-foreground">
                      {keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* === License Tab === */}
        <TabsContent value="license">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-500" /> License</CardTitle>
              <CardDescription className="text-2xs">Software license management</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                {licenseStatus ? <LicenseStatus status={licenseStatus} /> : null}
                {isLicensed && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefreshValidity}
                    disabled={refreshingLicense}
                    className="h-8 text-xs shrink-0"
                  >
                    <RefreshCw className={cn("h-3 w-3 mr-1.5", refreshingLicense && "animate-spin")} />
                    {refreshingLicense ? "Checking…" : "Refresh validity"}
                  </Button>
                )}
              </div>
              {isLicensed && licenseInfo && (
                <div className="rounded-lg bg-muted/30 p-3 space-y-2 text-sm">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Registered License</p>
                  <p><span className="text-muted-foreground">Email:</span> <span className="font-mono">{licenseInfo.email}</span></p>
                  <p><span className="text-muted-foreground">License:</span> <code className="font-mono text-xs tracking-wider">{licenseInfo.license_key}</code></p>
                </div>
              )}
              {hardwareId && (
                <div className="rounded-lg border border-border/50 p-3 space-y-2">
                  <p className="text-2xs text-muted-foreground flex items-center gap-1.5">
                    <Cpu className="h-3 w-3" /> Hardware ID (for support — send to vendor when renewing)
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs font-mono bg-muted/50 rounded px-2 py-1.5 truncate" title={hardwareId}>
                      {hardwareId}
                    </code>
                    <button
                      type="button"
                      onClick={copyHardwareId}
                      className="shrink-0 p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                      title="Copy"
                    >
                      {hwIdCopied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>
              )}
              {!isLicensed && <><Separator /><LicenseInput onActivate={activateLicense} /></>}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

/** Reusable setting row layout */
function SettingRow({
  label,
  description,
  icon,
  children,
}: {
  label: string;
  description: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-xs font-medium">{label}</p>
          <p className="text-2xs text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function DemoTestCard() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const demoStartedRef = useRef(false);
  const demoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useTauriEvent<{ status: string }>("trading:engine_status", (data) => {
    if (demoStartedRef.current && data.status === "Idle") {
      demoStartedRef.current = false;
      setRunning(false);
      setResult("Demo complete");
      if (demoTimerRef.current) { clearTimeout(demoTimerRef.current); demoTimerRef.current = null; }
    }
  });

  const runDemo = async () => {
    setRunning(true);
    demoStartedRef.current = true;
    setResult(null);
    demoTimerRef.current = setTimeout(() => {
      if (demoStartedRef.current) {
        demoStartedRef.current = false;
        setRunning(false);
        setResult("Demo timed out");
      }
    }, 30000);
    try {
      await tradingApi.simulateDemo();
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setRunning(false);
      demoStartedRef.current = false;
      if (demoTimerRef.current) { clearTimeout(demoTimerRef.current); demoTimerRef.current = null; }
    }
  };

  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-violet-500" /> Demo Test
        </CardTitle>
        <CardDescription className="text-2xs">
          Simulate a full trading cycle (signals, entries, P&L updates, exits) without TWS.
          Watch the Positions, Analytics, and Log pages update in real-time.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-3">
          <Button size="sm" variant="outline" onClick={runDemo} disabled={running}>
            <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
            {running ? "Running\u2026" : "Run Demo Simulation"}
          </Button>
          {result && (
            <span className={`text-2xs ${result.startsWith("Error") ? "text-red-500" : "text-green-500"}`}>
              {result}
            </span>
          )}
        </div>
        <p className="text-2xs text-muted-foreground">
          Creates 3 fake option positions (AAPL, TSLA, SPY), updates P&L for ~12 seconds, then closes them.
          The full cycle takes about 20 seconds.
        </p>
      </CardContent>
    </Card>
  );
}

/** Display config section from settings file */
function ConfigSection({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <div>
      <p className="font-medium text-muted-foreground mb-1.5 text-2xs uppercase tracking-wider">{title}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between py-0.5">
            <span className="text-muted-foreground/60 text-2xs">{key.replace(/_/g, " ")}</span>
            <span className="font-mono text-2xs text-foreground/70">
              {Array.isArray(value)
                ? value.join(", ")
                : typeof value === "object"
                  ? JSON.stringify(value)
                  : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
