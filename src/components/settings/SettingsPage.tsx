import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";
import { useTheme } from "@/hooks/useTheme";
import { useLicense } from "@/hooks/useLicense";
import { config as configApi } from "@/lib/tauri-commands";
import { Save, Moon, Sun, Shield, Bell, Palette, Zap, KeyRound, Check, LayoutGrid, FileJson } from "lucide-react";
import { LicenseStatus } from "@/components/license/LicenseStatus";
import { LicenseInput } from "@/components/license/LicenseInput";

export function SettingsPage() {
  const { settings, updateSettings, tradingConfig } = useConfigStore();
  const { isDark, toggleTheme } = useTheme();
  const { licenseStatus, isLicensed, activateLicense, deactivateLicense } = useLicense();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [settingsFile, setSettingsFile] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    configApi.getSettingsFile().then(setSettingsFile).catch(() => setSettingsFile(null));
  }, []);

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
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Settings</h2>
          <p className="text-xs text-muted-foreground">Application configuration</p>
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saved ? <><Check className="h-3.5 w-3.5" /> Saved</> : <><Save className="h-3.5 w-3.5" /> {saving ? "Saving..." : "Save All"}</>}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Palette className="h-4 w-4 text-violet-500" /> Appearance</CardTitle>
          <CardDescription>Theme preferences</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDark ? <Moon className="h-4 w-4 text-blue-400" /> : <Sun className="h-4 w-4 text-amber-500" />}
              <div>
                <p className="text-sm font-medium">Dark Mode</p>
                <p className="text-2xs text-muted-foreground">Toggle dark/light theme</p>
              </div>
            </div>
            <Switch checked={isDark} onCheckedChange={toggleTheme} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Zap className="h-4 w-4 text-amber-500" /> Trading Mode</CardTitle>
          <CardDescription>Demo or live trading</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Live Trading</p>
              <p className="text-2xs text-muted-foreground">Enable real order execution</p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={settings.trading_mode === "live" ? "danger" : "secondary"} className="text-2xs">{settings.trading_mode.toUpperCase()}</Badge>
              <Switch checked={settings.trading_mode === "live"} onCheckedChange={(c) => updateSettings({ trading_mode: c ? "live" : "demo" })} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Bell className="h-4 w-4 text-blue-500" /> Notifications</CardTitle>
          <CardDescription>Alert preferences</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Show Notifications</p>
              <p className="text-2xs text-muted-foreground">Trade alerts and system events</p>
            </div>
            <Switch checked={settings.show_notifications} onCheckedChange={(c) => updateSettings({ show_notifications: c })} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><LayoutGrid className="h-4 w-4 text-amber-500" /> UI</CardTitle>
          <CardDescription>From config/settings.json (update interval, charts)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Update interval (ms)</p>
              <p className="text-2xs text-muted-foreground">Refresh rate for live data</p>
            </div>
            <Input
              type="number"
              className="w-24"
              value={settings.update_interval ?? 1000}
              onChange={(e) => updateSettings({ update_interval: parseInt(e.target.value, 10) || 1000 })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Show charts</p>
              <p className="text-2xs text-muted-foreground">Analytics and P&L charts</p>
            </div>
            <Switch checked={settings.show_charts ?? true} onCheckedChange={(c) => updateSettings({ show_charts: c })} />
          </div>
        </CardContent>
      </Card>

      {settingsFile && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2"><FileJson className="h-4 w-4 text-amber-500" /> From config/settings.json</CardTitle>
            <CardDescription>Values from project config/settings.json (merged on startup). Edit the file to change.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {settingsFile.trading && typeof settingsFile.trading === "object" ? (
              <div>
                <p className="font-medium text-muted-foreground mb-1">Trading</p>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  {(settingsFile.trading as Record<string, unknown>).symbols ? (
                    <li>Symbols: {(() => { const s = (settingsFile.trading as Record<string, unknown>).symbols; return Array.isArray(s) ? (s as string[]).join(", ") : String(s); })()}</li>
                  ) : null}
                  {(settingsFile.trading as Record<string, unknown>).contract_month ? (
                    <li>Contract month: {String((settingsFile.trading as Record<string, unknown>).contract_month)}</li>
                  ) : null}
                  {(settingsFile.trading as Record<string, unknown>).trading_hours ? (
                    <li>Hours: {JSON.stringify((settingsFile.trading as Record<string, unknown>).trading_hours)}</li>
                  ) : null}
                  {(settingsFile.trading as Record<string, unknown>).time_windows && Array.isArray((settingsFile.trading as Record<string, unknown>).time_windows) ? (
                    <li>Time windows: {((settingsFile.trading as Record<string, unknown>).time_windows as string[]).length} entries</li>
                  ) : null}
                  {(settingsFile.trading as Record<string, unknown>).daily_profit_limit != null ? (
                    <li>Daily profit limit: {Number((settingsFile.trading as Record<string, unknown>).daily_profit_limit)}</li>
                  ) : null}
                  {(settingsFile.trading as Record<string, unknown>).daily_loss_limit != null ? (
                    <li>Daily loss limit: {Number((settingsFile.trading as Record<string, unknown>).daily_loss_limit)}</li>
                  ) : null}
                </ul>
              </div>
            ) : null}
            {settingsFile.strategy && typeof settingsFile.strategy === "object" ? (
              <div>
                <p className="font-medium text-muted-foreground mb-1">Strategy</p>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  {(settingsFile.strategy as Record<string, unknown>).name ? (
                    <li>Name: {String((settingsFile.strategy as Record<string, unknown>).name)}</li>
                  ) : null}
                  {(settingsFile.strategy as Record<string, unknown>).atr_period != null ? (
                    <li>ATR period: {Number((settingsFile.strategy as Record<string, unknown>).atr_period)}</li>
                  ) : null}
                  {(settingsFile.strategy as Record<string, unknown>).sl_multiplier != null ? (
                    <li>SL multiplier: {Number((settingsFile.strategy as Record<string, unknown>).sl_multiplier)}</li>
                  ) : null}
                  {(settingsFile.strategy as Record<string, unknown>).tp_multiplier != null ? (
                    <li>TP multiplier: {Number((settingsFile.strategy as Record<string, unknown>).tp_multiplier)}</li>
                  ) : null}
                </ul>
              </div>
            ) : null}
            {settingsFile.broker && typeof settingsFile.broker === "object" ? (
              <div>
                <p className="font-medium text-muted-foreground mb-1">Broker (from file)</p>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  <li>Host: {String((settingsFile.broker as Record<string, unknown>).host ?? "—")}</li>
                  <li>Port: {String((settingsFile.broker as Record<string, unknown>).port ?? "—")}</li>
                  <li>Client ID: {String((settingsFile.broker as Record<string, unknown>).client_id ?? "—")}</li>
                </ul>
              </div>
            ) : null}
            {settingsFile.logging && typeof settingsFile.logging === "object" ? (
              <div>
                <p className="font-medium text-muted-foreground mb-1">Logging</p>
                <p className="text-muted-foreground">Level: {String((settingsFile.logging as Record<string, unknown>).level ?? "—")}</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-500" /> License</CardTitle>
          <CardDescription>Software license management</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {licenseStatus ? <LicenseStatus status={licenseStatus} /> : null}
          {!isLicensed && <><Separator /><LicenseInput onActivate={activateLicense} /></>}
          {isLicensed && (
            <><Separator /><Button variant="outline" size="sm" onClick={deactivateLicense} className="text-red-500 hover:bg-red-500/10"><KeyRound className="h-3.5 w-3.5 mr-1.5" /> Deactivate</Button></>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
