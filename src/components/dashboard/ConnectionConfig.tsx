import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";
import { useTradingStore } from "@/stores/tradingStore";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionConfig() {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  const { connectedToTws } = useTradingStore();
  if (!tradingConfig) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Connection
        </CardTitle>
        <Badge variant={connectedToTws ? "success" : "danger"} className="gap-1.5">
          {connectedToTws ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {connectedToTws ? "Connected" : "Disconnected"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2.5">
          <div className="space-y-1">
            <label className="text-2xs font-medium text-muted-foreground">IP</label>
            <Input value={tradingConfig.ip} onChange={(e) => updateTradingConfig({ ip: e.target.value })} placeholder="127.0.0.1" />
          </div>
          <div className="space-y-1">
            <label className="text-2xs font-medium text-muted-foreground">Port</label>
            <Input type="number" value={tradingConfig.port} onChange={(e) => updateTradingConfig({ port: parseInt(e.target.value) })} />
          </div>
          <div className="space-y-1">
            <label className="text-2xs font-medium text-muted-foreground">Client ID</label>
            <Input type="number" value={tradingConfig.client_id} onChange={(e) => updateTradingConfig({ client_id: parseInt(e.target.value) })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-2xs font-medium text-muted-foreground">Account</label>
            <Input value={tradingConfig.account_id} onChange={(e) => updateTradingConfig({ account_id: e.target.value })} placeholder="U1234567" />
          </div>
          <div className="space-y-1">
            <label className="text-2xs font-medium text-muted-foreground">Order Expiry (s)</label>
            <Input type="number" value={tradingConfig.order_expiry_timer} onChange={(e) => updateTradingConfig({ order_expiry_timer: parseInt(e.target.value) })} />
          </div>
        </div>
        <div className="flex items-center justify-between pt-1">
          <div>
            <p className="text-xs font-medium">Transmit Orders</p>
            <p className="text-2xs text-muted-foreground">Send orders to market</p>
          </div>
          <Switch checked={tradingConfig.order_transmit} onCheckedChange={(c) => updateTradingConfig({ order_transmit: c })} />
        </div>
      </CardContent>
    </Card>
  );
}
