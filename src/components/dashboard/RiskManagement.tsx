import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { useConfigStore } from "@/stores/configStore";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";

export function RiskManagement() {
  const { tradingConfig, updateTradingConfig } = useConfigStore();
  const { dailyPnl, totalTrades } = useTradingStore();
  if (!tradingConfig) return null;

  const profitPct = Math.min(100, Math.abs((dailyPnl.total / tradingConfig.profit_amount_day) * 100));
  const tradePct = Math.min(100, (totalTrades / tradingConfig.per_day_trades) * 100);

  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
          Risk
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-0.5">
            <label className="text-[9px] font-medium text-muted-foreground/50">Profit Target</label>
            <Input type="number" value={tradingConfig.profit_amount_day} onChange={(e) => updateTradingConfig({ profit_amount_day: parseFloat(e.target.value) })} />
          </div>
          <div className="space-y-0.5">
            <label className="text-[9px] font-medium text-muted-foreground/50">Loss Limit</label>
            <Input type="number" value={tradingConfig.loss_amount_day} onChange={(e) => updateTradingConfig({ loss_amount_day: parseFloat(e.target.value) })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-0.5">
            <label className="text-[9px] font-medium text-muted-foreground/50">Max Trades</label>
            <Input type="number" value={tradingConfig.per_day_trades} onChange={(e) => updateTradingConfig({ per_day_trades: parseInt(e.target.value) })} />
          </div>
          <div className="space-y-0.5">
            <label className="text-[9px] font-medium text-muted-foreground/50">Max Contract $</label>
            <Input type="number" value={tradingConfig.max_contract_amount} onChange={(e) => updateTradingConfig({ max_contract_amount: parseFloat(e.target.value) })} />
          </div>
        </div>
        <div className="space-y-0.5">
          <label className="text-[9px] font-medium text-muted-foreground/50">Trailing Increment</label>
          <Input type="number" step="0.01" value={tradingConfig.profit_increment} onChange={(e) => updateTradingConfig({ profit_increment: parseFloat(e.target.value) })} />
        </div>

        <div className="pt-2 mt-0.5 border-t border-border/20 space-y-2">
          <div>
            <div className="flex items-center justify-between text-[10px] mb-1">
              <span className="text-muted-foreground/50">P&L</span>
              <span className={cn("font-mono font-bold tabular-nums text-[11px]", pnlColor(dailyPnl.total))}>
                {formatCurrency(dailyPnl.total)}
              </span>
            </div>
            <Progress value={profitPct} indicatorClassName={dailyPnl.total >= 0 ? "bg-emerald-500" : "bg-red-500"} />
          </div>
          <div>
            <div className="flex items-center justify-between text-[10px] mb-1">
              <span className="text-muted-foreground/50">Trades</span>
              <span className="font-mono font-bold tabular-nums text-[11px]">
                {totalTrades}/{tradingConfig.per_day_trades}
              </span>
            </div>
            <Progress value={tradePct} indicatorClassName="bg-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
