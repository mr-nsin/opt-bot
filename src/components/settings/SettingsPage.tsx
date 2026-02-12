import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";
import { useTheme } from "@/hooks/useTheme";
import { useLicense } from "@/hooks/useLicense";
import { config as configApi } from "@/lib/tauri-commands";
import { Save, Moon, Sun, Shield, Bell, Palette, Zap, KeyRound, Check } from "lucide-react";
import { LicenseStatus } from "@/components/license/LicenseStatus";
import { LicenseInput } from "@/components/license/LicenseInput";

export function SettingsPage() {
  const { settings, updateSettings, tradingConfig } = useConfigStore();
  const { isDark, toggleTheme } = useTheme();
  const { licenseStatus, isLicensed, activateLicense, deactivateLicense } = useLicense();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

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
          <CardTitle className="text-sm flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-500" /> License</CardTitle>
          <CardDescription>Software license management</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {licenseStatus && <LicenseStatus status={licenseStatus} />}
          {!isLicensed && <><Separator /><LicenseInput onActivate={activateLicense} /></>}
          {isLicensed && (
            <><Separator /><Button variant="outline" size="sm" onClick={deactivateLicense} className="text-red-500 hover:bg-red-500/10"><KeyRound className="h-3.5 w-3.5 mr-1.5" /> Deactivate</Button></>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
