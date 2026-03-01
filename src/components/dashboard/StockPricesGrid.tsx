import { memo } from "react";
import { TrendingUp, TrendingDown, Minus, BarChart2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";

interface TickItem {
  symbol: string;
  last: number;
  bid?: number;
  ask?: number;
  volume?: number;
  change?: number;
  changePct?: number;
}

const PRIORITY_SYMBOLS = ["SPY", "QQQ", "VIX", "TSLA", "AAPL", "NVDA", "AMD", "MSFT", "AMZN", "BABA"];

/** Grid of stock symbols with last price, bid/ask, and change. Shown on Overview below Account Summary + Data feed. */
export const StockPricesGrid = memo(function StockPricesGrid() {
  const dataStatus = useTradingStore((s) => s.dataStatus);
  const rawSample = (dataStatus as Record<string, unknown>)?.stock_ticks_sample;
  const ticks: TickItem[] = Array.isArray(rawSample)
    ? (rawSample as TickItem[]).filter((t) => t && typeof t.symbol === "string")
    : [];
  const symbolsFromStatus = Array.isArray((dataStatus as Record<string, unknown>)?.symbols)
    ? ((dataStatus as Record<string, unknown>).symbols as string[])
    : [];

  const sorted = [...ticks].sort((a, b) => {
    const ai = PRIORITY_SYMBOLS.indexOf(a.symbol);
    const bi = PRIORITY_SYMBOLS.indexOf(b.symbol);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  // When we have no tick data but we know configured symbols, show placeholders so the grid isn't empty
  const placeholders: TickItem[] =
    sorted.length === 0 && symbolsFromStatus.length > 0
      ? symbolsFromStatus.slice(0, 15).map((symbol) => ({ symbol, last: 0 }))
      : [];

  const displayList = sorted.length > 0 ? sorted : placeholders;
  const isEmpty = displayList.length === 0;

  if (isEmpty) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-primary/80" />
            Stock prices
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground text-center py-4">
            Start trading to see live prices (updates with data feed).
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <BarChart2 className="h-5 w-5 text-primary/80" />
          Stock prices
        </CardTitle>
      </CardHeader>
      <CardContent>
        {placeholders.length > 0 && (
          <p className="text-xs text-muted-foreground mb-2">
            Configured symbols — waiting for live ticks from TWS (start trading and ensure STK/FUT are subscribed).
          </p>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {displayList.map((tick) => {
            const change = tick.change ?? 0;
            const changePct = tick.changePct ?? 0;
            const isUp = change > 0;
            const isDown = change < 0;
            const ChangeIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;
            const changeColor = isUp ? "text-emerald-500" : isDown ? "text-red-500" : "text-muted-foreground";
            const isPlaceholder = tick.last === 0 && placeholders.length > 0;
            return (
              <div
                key={tick.symbol}
                className={cn(
                  "flex flex-col p-2.5 rounded-lg border border-border/15 min-w-0 overflow-hidden",
                  isPlaceholder ? "bg-muted/5" : "bg-muted/10 hover:bg-muted/20",
                  "transition-colors"
                )}
              >
                <div className="flex items-center justify-between gap-1 mb-0.5">
                  <span className="font-mono font-bold text-xs truncate">{tick.symbol}</span>
                  {!isPlaceholder && <ChangeIcon className={cn("h-3 w-3 shrink-0", changeColor)} />}
                </div>
                <span className={cn("font-mono font-semibold tabular-nums text-sm", changeColor)}>
                  {tick.last > 0 ? tick.last.toFixed(2) : "—"}
                </span>
                {(tick.bid !== undefined || tick.ask !== undefined) && (
                  <div className="flex items-center gap-1 mt-0.5 text-2xs font-mono tabular-nums text-muted-foreground">
                    {tick.bid !== undefined && <span className="text-emerald-500/80">B:{tick.bid.toFixed(2)}</span>}
                    {tick.bid !== undefined && tick.ask !== undefined && <span>/</span>}
                    {tick.ask !== undefined && <span className="text-red-500/80">A:{tick.ask.toFixed(2)}</span>}
                  </div>
                )}
                {changePct !== 0 && (
                  <span className={cn("text-2xs font-mono tabular-nums mt-0.5", changeColor)}>
                    {changePct > 0 ? "+" : ""}{changePct.toFixed(2)}%
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
