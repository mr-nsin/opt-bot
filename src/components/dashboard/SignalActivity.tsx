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
}

/** Displays the latest detected signals with a timeline view. */
export const SignalActivity = memo(function SignalActivity() {
  const lastSignal = useTradingStore((s) => s.lastSignal);
  const todayTrades = useTradingStore((s) => s.todayTrades);

  // Build signal entries from trades + last signal
  const signals: SignalEntry[] = [];
  if (lastSignal?.symbol) {
    signals.push({
      symbol: lastSignal.symbol as string,
      direction: (lastSignal.direction as string) ?? "UNKNOWN",
      strength: lastSignal.strength as string | undefined,
      timestamp: lastSignal.timestamp as string | undefined,
      indicator: lastSignal.indicator as string | undefined,
    });
  }

  // Add recent trades as executed signals
  todayTrades.slice(0, 5).forEach((trade) => {
    if (trade.symbol) {
      signals.push({
        symbol: trade.symbol,
        direction: (trade.direction as string) ?? (trade.right === "C" ? "CALL" : trade.right === "P" ? "PUT" : "—"),
        strength: "executed",
        timestamp: trade.timestamp as string | undefined,
        indicator: "trade",
      });
    }
  });

  const isCall = (dir: string) =>
    ["CALL", "BUY", "LONG", "C"].includes(dir.toUpperCase());

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
          <Zap className="h-3 w-3 text-violet-400/70" />
          Signal Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {signals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-5 text-center">
            <BarChart3 className="h-6 w-6 text-muted-foreground/15 mb-1.5" />
            <p className="text-[11px] text-muted-foreground/50">
              No signals detected yet
            </p>
            <p className="text-[9px] text-muted-foreground/30 mt-0.5">
              Signals appear when opportunities are detected
            </p>
          </div>
        ) : (
          <div className="space-y-0">
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
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-[11px]">
                      {sig.symbol}
                    </span>
                    <Badge
                      variant={isCall(sig.direction) ? "success" : "danger"}
                      className="text-[9px] px-1 py-0 h-3.5"
                    >
                      {sig.direction.toUpperCase()}
                    </Badge>
                    {sig.strength && sig.strength !== "executed" && (
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5">
                        {sig.strength}
                      </Badge>
                    )}
                    {sig.strength === "executed" && (
                      <Badge variant="default" className="text-[9px] px-1 py-0 h-3.5 bg-blue-500/10 text-blue-500 border-transparent">
                        Filled
                      </Badge>
                    )}
                  </div>
                  {sig.indicator && (
                    <span className="text-[9px] text-muted-foreground/50">
                      via {sig.indicator}
                    </span>
                  )}
                </div>

                {/* Timestamp */}
                {sig.timestamp && (
                  <span className="text-[9px] text-muted-foreground/40 font-mono tabular-nums shrink-0">
                    {new Date(sig.timestamp).toLocaleTimeString("en-US", {
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
