import { memo, useEffect, useRef, useState } from "react";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface TickerItem {
  symbol: string;
  last: number;
  change?: number;
  changePct?: number;
  bid?: number;
  ask?: number;
  volume?: number;
}

/** Static fallback tickers when no live data */
const STATIC_TICKERS: TickerItem[] = [
  { symbol: "SPY", last: 0 },
  { symbol: "QQQ", last: 0 },
  { symbol: "TSLA", last: 0 },
  { symbol: "AAPL", last: 0 },
  { symbol: "NVDA", last: 0 },
  { symbol: "AMD", last: 0 },
  { symbol: "MSFT", last: 0 },
  { symbol: "AMZN", last: 0 },
];

/**
 * MarketTicker — A horizontal scrolling market ticker strip showing live prices.
 * Sits between the header and the main content area.
 * Inspired by TradingView's top ticker and Bloomberg Terminal's price bar.
 */
export const MarketTicker = memo(function MarketTicker() {
  const dataStatus = useTradingStore((s) => s.dataStatus);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const [prevPrices, setPrevPrices] = useState<Record<string, number>>({});
  const [flashMap, setFlashMap] = useState<Record<string, "up" | "down" | null>>({});

  // Extract ticks from data status
  const ticks: TickerItem[] =
    (dataStatus as Record<string, unknown>)?.stock_ticks_sample
      ? ((dataStatus as Record<string, unknown>).stock_ticks_sample as TickerItem[])
      : [];

  const items = ticks.length > 0 ? ticks : STATIC_TICKERS;

  // Priority sort
  const priorityOrder = ["SPY", "QQQ", "VIX", "TSLA", "AAPL", "NVDA", "AMD", "MSFT", "AMZN", "BABA"];
  const sorted = [...items].sort((a, b) => {
    const ai = priorityOrder.indexOf(a.symbol);
    const bi = priorityOrder.indexOf(b.symbol);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  // Flash detection on price change
  useEffect(() => {
    const newFlashes: Record<string, "up" | "down" | null> = {};
    const newPrices: Record<string, number> = {};

    for (const t of sorted) {
      newPrices[t.symbol] = t.last;
      const prev = prevPrices[t.symbol];
      if (prev !== undefined && prev !== t.last) {
        newFlashes[t.symbol] = t.last > prev ? "up" : "down";
      }
    }

    if (Object.keys(newFlashes).length > 0) {
      setFlashMap((f) => ({ ...f, ...newFlashes }));
      const timer = setTimeout(() => {
        setFlashMap((f) => {
          const next = { ...f };
          for (const key of Object.keys(newFlashes)) {
            next[key] = null;
          }
          return next;
        });
      }, 400);
      setPrevPrices(newPrices);
      return () => clearTimeout(timer);
    }
    setPrevPrices(newPrices);
  }, [sorted.map((t) => `${t.symbol}:${t.last}`).join(",")]);

  return (
    <div className="h-7 bg-card/80 backdrop-blur-sm border-b border-border/50 flex items-center overflow-hidden shrink-0">
      {/* Live indicator */}
      <div className="flex items-center gap-1.5 px-3 border-r border-border/30 h-full shrink-0">
        {connectedToTws ? (
          <>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 live-dot" />
            <span className="text-2xs font-semibold text-emerald-500 tracking-wider">LIVE</span>
          </>
        ) : (
          <>
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
            <span className="text-2xs font-semibold text-muted-foreground/50 tracking-wider">MKTD</span>
          </>
        )}
      </div>

      {/* Scrolling ticker area */}
      <div className="flex-1 overflow-x-auto no-scrollbar">
        <div className="flex items-center h-full gap-0">
          {sorted.map((tick) => {
            const change = tick.change ?? 0;
            const changePct = tick.changePct ?? 0;
            const isUp = change > 0;
            const isDown = change < 0;
            const flash = flashMap[tick.symbol];
            const ChangeIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

            return (
              <div
                key={tick.symbol}
                className={cn(
                  "flex items-center gap-1.5 px-3 h-full border-r border-border/20 transition-colors duration-300 cursor-default select-none",
                  flash === "up" && "bg-emerald-500/10",
                  flash === "down" && "bg-red-500/10"
                )}
              >
                {/* Symbol */}
                <span className="text-2xs font-bold text-foreground/80 tracking-wide">
                  {tick.symbol}
                </span>

                {/* Price */}
                <span
                  className={cn(
                    "font-mono font-semibold tabular-nums text-2xs",
                    tick.last === 0
                      ? "text-muted-foreground/30"
                      : isUp
                        ? "text-emerald-500"
                        : isDown
                          ? "text-red-500"
                          : "text-foreground/70"
                  )}
                >
                  {tick.last === 0 ? "—" : tick.last.toFixed(2)}
                </span>

                {/* Change arrow */}
                {tick.last > 0 && (
                  <ChangeIcon
                    className={cn(
                      "h-2.5 w-2.5",
                      isUp ? "text-emerald-500/70" : isDown ? "text-red-500/70" : "text-muted-foreground/30"
                    )}
                  />
                )}

                {/* Change % */}
                {changePct !== 0 && (
                  <span
                    className={cn(
                      "font-mono tabular-nums text-2xs",
                      isUp ? "text-emerald-500/60" : "text-red-500/60"
                    )}
                  >
                    {changePct > 0 ? "+" : ""}{changePct.toFixed(2)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});
