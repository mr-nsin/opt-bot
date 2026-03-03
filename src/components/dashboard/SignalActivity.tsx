import { memo } from "react";
import { Zap, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";

interface SignalEntry {
  symbol: string;
  direction: string;
  strength?: string;
  timestamp?: string;
  indicator?: string;
  price?: number;
  strike?: number;
  expiry?: string;
  isTrade?: boolean;
}

function resolveDirection(s: { direction?: string; signal_type?: string; right?: string }): string {
  const d = (s.direction ?? s.signal_type ?? "").toString().toUpperCase();
  if (d && d !== "UNKNOWN") return d;
  if (s.right === "C" || s.right === "CALL") return "CALL";
  if (s.right === "P" || s.right === "PUT") return "PUT";
  return "—";
}

/** Displays signals detected in session with a grid view. */
export const SignalActivity = memo(function SignalActivity() {
  const signalsInSession = useTradingStore((s) => s.signalsInSession);
  const todayTrades = useTradingStore((s) => s.todayTrades);

  // Build grid: session signals first, then executed trades
  const signals: SignalEntry[] = signalsInSession.map((s) => ({
    symbol: (s.symbol ?? "") as string,
    direction: resolveDirection(s),
    strength: (s.strength ?? s.reason) as string | undefined,
    timestamp: s.timestamp as string | undefined,
    indicator: s.indicator as string | undefined,
    price: typeof s.price === "number" ? s.price : undefined,
    strike: typeof s.strike === "number" ? s.strike : undefined,
    expiry: s.expiry as string | undefined,
    isTrade: false,
  }));

  todayTrades.slice(0, 10).forEach((trade) => {
    if (trade.symbol) {
      signals.push({
        symbol: trade.symbol,
        direction: resolveDirection(trade),
        strength: "executed",
        timestamp: trade.timestamp as string | undefined,
        indicator: "trade",
        price: trade.entry_price ?? trade.exit_price,
        strike: typeof trade.strike === "number" ? trade.strike : undefined,
        expiry: trade.expiry as string | undefined,
        isTrade: true,
      });
    }
  });

  const isCall = (dir: string) =>
    ["CALL", "BUY", "LONG", "C"].includes(dir.toUpperCase());

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Zap className="h-5 w-5 text-primary/80" />
          Signal Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {signals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-5 text-center">
            <BarChart3 className="h-6 w-6 text-muted-foreground/15 mb-1.5" />
            <p className="text-2xs text-muted-foreground/70">
              No signals detected yet
            </p>
            <p className="text-2xs text-muted-foreground/50 mt-0.5">
              Signals appear when opportunities are detected
            </p>
          </div>
        ) : (
          <div className="space-y-0">
            {/* Grid header */}
            <div className="grid grid-cols-[auto_1fr_auto_auto] gap-2 py-1.5 px-1.5 text-xs text-muted-foreground/60 font-medium border-b border-border/20 mb-1">
              <span className="w-6" />
              <span>Symbol · Direction · Strike · Price · Expiry</span>
              <span className="tabular-nums">Date/Time</span>
            </div>
            {signals.map((sig, i) => (
              <div
                key={`${sig.symbol}-${i}`}
                className={cn(
                  "flex items-center gap-2 py-1.5 px-1.5 rounded-md transition-colors",
                  i === 0 && "bg-muted/30 signal-glow",
                  i > 0 && "border-t border-border/20"
                )}
              >
                {/* Direction icon */}
                <div
                  className={cn(
                    "flex items-center justify-center h-6 w-6 rounded shrink-0",
                    isCall(sig.direction)
                      ? "bg-emerald-500/8 text-emerald-500"
                      : "bg-red-500/8 text-red-500"
                  )}
                >
                  {isCall(sig.direction) ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                </div>

                {/* Signal info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-mono font-bold text-xs">
                      {sig.symbol}
                    </span>
                    <Badge
                      variant={isCall(sig.direction) ? "success" : "danger"}
                      className="text-xs px-1.5 py-0 h-4"
                    >
                      {sig.direction.toUpperCase()}
                    </Badge>
                    {sig.strike != null && sig.strike > 0 && (
                      <span className="text-xs text-muted-foreground font-mono">
                        ${Number(sig.strike).toFixed(1)}
                      </span>
                    )}
                    {sig.price != null && sig.price > 0 && (
                      <span className="text-xs text-muted-foreground font-mono">
                        @ ${Number(sig.price).toFixed(2)}
                      </span>
                    )}
                    {sig.expiry && (
                      <span className="text-xs text-muted-foreground/80 font-mono">
                        exp:{sig.expiry}
                      </span>
                    )}
                    {sig.strength && sig.strength !== "executed" && (
                      <Badge variant="outline" className="text-xs px-1.5 py-0 h-4">
                        {sig.strength}
                      </Badge>
                    )}
                    {sig.strength === "executed" && (
                      <Badge variant="default" className="text-xs px-1.5 py-0 h-4 bg-blue-500/10 text-blue-500 border-transparent">
                        Filled
                      </Badge>
                    )}
                  </div>
                  {sig.indicator && (
                    <span className="text-xs text-muted-foreground/60">
                      via {sig.indicator}
                    </span>
                  )}
                </div>

                {/* Timestamp */}
                {sig.timestamp && (
                  <span className="text-xs text-muted-foreground/50 font-mono tabular-nums shrink-0" title={sig.timestamp}>
                    {new Date(sig.timestamp).toLocaleString("en-US", {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      hour12: false,
                    })}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
