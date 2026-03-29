import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useConfigStore } from "@/stores/configStore";
import { useTradingStore } from "@/stores/tradingStore";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionConfig({ disabled }: { disabled?: boolean }) {
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
            <label className="text-xs font-medium text-muted-foreground">IP</label>
            <Input value={tradingConfig.ip} onChange={(e) => !disabled && updateTradingConfig({ ip: e.target.value })} placeholder="127.0.0.1" disabled={disabled} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Port</label>
            <Input type="number" value={tradingConfig.port} onChange={(e) => !disabled && updateTradingConfig({ port: parseInt(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Client ID</label>
            <Input type="number" value={tradingConfig.client_id} onChange={(e) => !disabled && updateTradingConfig({ client_id: parseInt(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Account</label>
            <Input value={tradingConfig.account_id} onChange={(e) => !disabled && updateTradingConfig({ account_id: e.target.value })} placeholder="Optional — leave empty for all" disabled={disabled} />
            <p className="text-[10px] text-muted-foreground leading-snug">
              Empty: show every account&apos;s positions. Set to your IB id for order routing and to hide other accounts in the Positions tab. Wrong id hides legs until fixed or cleared.
            </p>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Order Expiry (s)</label>
            <Input type="number" value={tradingConfig.order_expiry_timer} onChange={(e) => !disabled && updateTradingConfig({ order_expiry_timer: parseInt(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="flex items-center justify-between pt-1">
          <div>
            <p className="text-xs font-medium">Transmit Orders</p>
            <p className="text-xs text-muted-foreground">Send orders to market</p>
          </div>
          <Switch checked={tradingConfig.order_transmit} onCheckedChange={(c) => !disabled && updateTradingConfig({ order_transmit: c })} disabled={disabled} />
        </div>
      </CardContent>
    </Card>
  );
}
