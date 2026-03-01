import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import { CANDLE_TIMEFRAMES, EXPIRY_OPTIONS } from "@/lib/constants";

export function TradeParameters() {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  if (!tradingConfig) return null;

  const sel = "flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 focus-visible:border-primary/50";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Parameters
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Expiry</label>
            <select value={tradingConfig.spy_qqq_expiry} onChange={(e) => updateTradingConfig({ spy_qqq_expiry: e.target.value })} className={sel}>
              {EXPIRY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Candle</label>
            <select value={tradingConfig.candle_time} onChange={(e) => updateTradingConfig({ candle_time: e.target.value })} className={sel}>
              {CANDLE_TIMEFRAMES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Call Delta</label>
            <Input type="number" step="0.01" value={tradingConfig.call_delta_check} onChange={(e) => updateTradingConfig({ call_delta_check: parseFloat(e.target.value) })} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Put Delta</label>
            <Input type="number" step="0.01" value={tradingConfig.put_delta_check} onChange={(e) => updateTradingConfig({ put_delta_check: parseFloat(e.target.value) })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Quantity</label>
            <Input type="number" value={tradingConfig.quantity} onChange={(e) => updateTradingConfig({ quantity: parseInt(e.target.value) })} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Cooldown (s)</label>
            <Input type="number" value={tradingConfig.distance_between_trade} onChange={(e) => updateTradingConfig({ distance_between_trade: parseInt(e.target.value) })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">ATR Value</label>
            <Input type="number" step="0.01" value={tradingConfig.atr_value} onChange={(e) => updateTradingConfig({ atr_value: parseFloat(e.target.value) })} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Body Mult.</label>
            <Input type="number" step="0.1" value={tradingConfig.body} onChange={(e) => updateTradingConfig({ body: parseFloat(e.target.value) })} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
