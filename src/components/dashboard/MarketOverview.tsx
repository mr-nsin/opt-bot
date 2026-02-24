import { memo } from "react";
import { Activity, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";

interface TickSample {
  symbol: string;
  last: number;
  bid?: number;
  ask?: number;
  volume?: number;
  change?: number;
}

/** Market overview showing live tick data for watched symbols. */
export const MarketOverview = memo(function MarketOverview() {
  const dataStatus = useTradingStore((s) => s.dataStatus);

  // Extract stock tick samples from data status
  const ticks: TickSample[] = (dataStatus as Record<string, unknown>)?.stock_ticks_sample
    ? ((dataStatus as Record<string, unknown>).stock_ticks_sample as TickSample[])
    : [];

  if (ticks.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-cyan-500" />
            Market Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground text-center py-4">
            Awaiting market data…
          </p>
        </CardContent>
      </Card>
    );
  }

  // Highlight key index-like symbols first
  const prioritySymbols = ["SPY", "QQQ", "VIX", "TSLA", "AAPL", "NVDA", "AMD", "MSFT", "AMZN", "BABA"];
  const sorted = [...ticks].sort((a, b) => {
    const ai = prioritySymbols.indexOf(a.symbol);
    const bi = prioritySymbols.indexOf(b.symbol);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-cyan-500" />
            Market Overview
          </span>
          <Badge variant="success" className="text-2xs gap-1 animate-pulse">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            LIVE
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {sorted.slice(0, 12).map((tick) => {
            const change = tick.change ?? 0;
            const changeColor =
              change > 0
                ? "text-emerald-500"
                : change < 0
                  ? "text-red-500"
                  : "text-muted-foreground";
            const ChangeIcon =
              change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus;

            return (
              <div
                key={tick.symbol}
                className={cn(
                  "flex flex-col p-2 rounded-lg border border-border/40 bg-muted/20",
                  "hover:bg-muted/40 transition-colors"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono font-bold text-xs">
                    {tick.symbol}
                  </span>
                  <ChangeIcon className={cn("h-3 w-3", changeColor)} />
                </div>
                <span className="font-mono font-semibold tabular-nums text-sm">
                  {typeof tick.last === "number" ? tick.last.toFixed(2) : "—"}
                </span>
                {tick.bid !== undefined && tick.ask !== undefined && (
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-2xs text-emerald-500/70 font-mono tabular-nums">
                      B:{tick.bid.toFixed(2)}
                    </span>
                    <span className="text-2xs text-muted-foreground/40">|</span>
                    <span className="text-2xs text-red-500/70 font-mono tabular-nums">
                      A:{tick.ask.toFixed(2)}
                    </span>
                  </div>
                )}
                {tick.volume !== undefined && tick.volume > 0 && (
                  <span className="text-2xs text-muted-foreground/50 font-mono tabular-nums mt-0.5">
                    Vol: {(tick.volume / 1000).toFixed(0)}K
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
});
