import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import { CANDLE_TIMEFRAMES, STOCK_EXPIRY_OPTIONS, SPY_QQQ_EXPIRY_OPTIONS } from "@/lib/constants";

export function TradeParameters({ disabled }: { disabled?: boolean }) {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  if (!tradingConfig) return null;

  const sel = "flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 focus-visible:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Parameters
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Stock Expiry (AMZN, AAPL…)</label>
            <select value={tradingConfig.expiry_to_trade ?? "next"} onChange={(e) => !disabled && updateTradingConfig({ expiry_to_trade: e.target.value })} className={sel} disabled={disabled}>
              {STOCK_EXPIRY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">SPY/QQQ Expiry</label>
            <select value={tradingConfig.spy_qqq_expiry ?? "0DTE"} onChange={(e) => !disabled && updateTradingConfig({ spy_qqq_expiry: e.target.value })} className={sel} disabled={disabled}>
              {SPY_QQQ_EXPIRY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Candle</label>
            <select value={tradingConfig.candle_time} onChange={(e) => !disabled && updateTradingConfig({ candle_time: e.target.value })} className={sel} disabled={disabled}>
              {CANDLE_TIMEFRAMES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Call Delta</label>
            <Input type="number" step="0.01" value={tradingConfig.call_delta_check} onChange={(e) => !disabled && updateTradingConfig({ call_delta_check: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Put Delta</label>
            <Input type="number" step="0.01" value={tradingConfig.put_delta_check} onChange={(e) => !disabled && updateTradingConfig({ put_delta_check: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Quantity</label>
            <Input type="number" value={tradingConfig.quantity} onChange={(e) => !disabled && updateTradingConfig({ quantity: parseInt(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Cooldown (s)</label>
            <Input type="number" value={tradingConfig.distance_between_trade ?? 610} onChange={(e) => !disabled && updateTradingConfig({ distance_between_trade: parseInt(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">ATR Value</label>
            <Input type="number" step="0.01" value={tradingConfig.atr_value} onChange={(e) => !disabled && updateTradingConfig({ atr_value: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Body Mult.</label>
            <Input type="number" step="0.1" value={tradingConfig.body} onChange={(e) => !disabled && updateTradingConfig({ body: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
