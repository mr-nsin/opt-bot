import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { useConfigStore } from "@/stores/configStore";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";

export function RiskManagement({ disabled }: { disabled?: boolean }) {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  if (!tradingConfig) return null;

  const profitPct = Math.min(100, Math.abs((dailyPnl.total / tradingConfig.profit_amount_day) * 100));
  const tradePct = Math.min(100, (totalTrades / tradingConfig.per_day_trades) * 100);

  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-foreground">
          Risk
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-0.5">
            <label className="text-sm font-semibold text-muted-foreground">Profit Target</label>
            <Input type="number" value={tradingConfig.profit_amount_day} onChange={(e) => !disabled && updateTradingConfig({ profit_amount_day: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-0.5">
            <label className="text-sm font-semibold text-muted-foreground">Loss Limit</label>
            <Input type="number" value={tradingConfig.loss_amount_day} onChange={(e) => !disabled && updateTradingConfig({ loss_amount_day: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-0.5">
            <label className="text-sm font-semibold text-muted-foreground">Max Trades</label>
            <Input type="number" value={tradingConfig.per_day_trades} onChange={(e) => !disabled && updateTradingConfig({ per_day_trades: parseInt(e.target.value) })} disabled={disabled} />
          </div>
          <div className="space-y-0.5">
            <label className="text-sm font-semibold text-muted-foreground">Max Contract $</label>
            <Input type="number" value={tradingConfig.max_contract_amount} onChange={(e) => !disabled && updateTradingConfig({ max_contract_amount: parseFloat(e.target.value) })} disabled={disabled} />
          </div>
        </div>
        <div className="space-y-0.5">
          <label className="text-sm font-semibold text-muted-foreground">Trailing Increment</label>
          <Input type="number" step="0.01" value={tradingConfig.profit_increment} onChange={(e) => !disabled && updateTradingConfig({ profit_increment: parseFloat(e.target.value) })} disabled={disabled} />
        </div>

        <div className="pt-2 mt-1 border-t border-border/30 space-y-2">
          <p className="text-xs font-semibold text-foreground/90">Entry stop / take profit</p>
          <p className="text-2xs text-muted-foreground leading-snug">
            Dynamic uses ATR vs premium rules. Fixed sets TP/SL as % of option entry. Saved with Save Configuration.
          </p>
          <div className="space-y-0.5">
            <label className="text-sm font-semibold text-muted-foreground">SL/TP mode</label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-2 text-sm disabled:opacity-50"
              value={tradingConfig.sl_tp_mode === "fixed_percent" ? "fixed_percent" : "dynamic_atr"}
              onChange={(e) => {
                if (disabled) return;
                const v = e.target.value;
                updateTradingConfig({
                  sl_tp_mode: v,
                  ...(v === "fixed_percent" ? { trailing_take_profit: false } : {}),
                });
              }}
              disabled={disabled}
            >
              <option value="dynamic_atr">Dynamic (ATR-based)</option>
              <option value="fixed_percent">Fixed (% of premium)</option>
            </select>
          </div>
          {tradingConfig.sl_tp_mode === "fixed_percent" && (
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-0.5">
                <label className="text-sm font-semibold text-muted-foreground">TP %</label>
                <Input
                  type="number"
                  min={0.01}
                  step={0.5}
                  value={tradingConfig.fixed_take_profit_percent ?? 30}
                  onChange={(e) =>
                    !disabled &&
                    updateTradingConfig({ fixed_take_profit_percent: parseFloat(e.target.value) || 30 })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="space-y-0.5">
                <label className="text-sm font-semibold text-muted-foreground">SL %</label>
                <Input
                  type="number"
                  min={0.01}
                  step={0.5}
                  value={tradingConfig.fixed_stop_loss_percent ?? 30}
                  onChange={(e) =>
                    !disabled &&
                    updateTradingConfig({ fixed_stop_loss_percent: parseFloat(e.target.value) || 30 })
                  }
                  disabled={disabled}
                />
              </div>
            </div>
          )}
          {tradingConfig.sl_tp_mode !== "fixed_percent" && (
            <div className="flex items-center justify-between gap-2 py-1">
              <div>
                <p className="text-sm font-semibold text-muted-foreground">Trailing take-profit</p>
                <p className="text-2xs text-muted-foreground">Trail target with pullback exit (uses increment above)</p>
              </div>
              <Switch
                checked={tradingConfig.trailing_take_profit !== false}
                onCheckedChange={(c) => !disabled && updateTradingConfig({ trailing_take_profit: c })}
                disabled={disabled}
              />
            </div>
          )}
        </div>

        <div className="pt-2 mt-0.5 border-t border-border/20 space-y-2">
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground font-medium">P&L</span>
              <span className={cn("font-mono font-bold tabular-nums text-sm", pnlColor(dailyPnl.total))}>
                {formatCurrency(dailyPnl.total)}
              </span>
            </div>
            <Progress value={profitPct} indicatorClassName={dailyPnl.total >= 0 ? "bg-emerald-500" : "bg-red-500"} />
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground font-medium">Trades (Open / Closed)</span>
              <span className="font-mono font-bold tabular-nums text-sm">
                {openTrades} open / {closedTrades} closed — {totalTrades}/{tradingConfig.per_day_trades} limit
              </span>
            </div>
            <Progress value={tradePct} indicatorClassName="bg-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
