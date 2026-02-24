import { memo } from "react";
import { Zap, TrendingUp, TrendingDown, Clock, BarChart3 } from "lucide-react";
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
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Zap className="h-3.5 w-3.5 text-violet-500" />
          Signal Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {signals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <BarChart3 className="h-8 w-8 text-muted-foreground/30 mb-2" />
            <p className="text-xs text-muted-foreground">
              No signals detected yet
            </p>
            <p className="text-2xs text-muted-foreground/60 mt-0.5">
              Signals appear when the engine detects trading opportunities
            </p>
          </div>
        ) : (
          <div className="space-y-0">
            {signals.map((sig, i) => (
              <div
                key={`${sig.symbol}-${i}`}
                className={cn(
                  "flex items-center gap-3 py-2 px-1 rounded-md transition-colors",
                  i === 0 && "bg-muted/40 signal-glow",
                  i > 0 && "border-t border-border/40"
                )}
              >
                {/* Direction icon */}
                <div
                  className={cn(
                    "flex items-center justify-center h-7 w-7 rounded-md shrink-0",
                    isCall(sig.direction)
                      ? "bg-emerald-500/10 text-emerald-500"
                      : "bg-red-500/10 text-red-500"
                  )}
                >
                  {isCall(sig.direction) ? (
                    <TrendingUp className="h-3.5 w-3.5" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5" />
                  )}
                </div>

                {/* Signal info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-xs">
                      {sig.symbol}
                    </span>
                    <Badge
                      variant={isCall(sig.direction) ? "success" : "danger"}
                      className="text-2xs px-1.5 py-0"
                    >
                      {sig.direction.toUpperCase()}
                    </Badge>
                    {sig.strength && sig.strength !== "executed" && (
                      <Badge variant="outline" className="text-2xs px-1.5 py-0">
                        {sig.strength}
                      </Badge>
                    )}
                    {sig.strength === "executed" && (
                      <Badge variant="default" className="text-2xs px-1.5 py-0 bg-blue-500/10 text-blue-500 border-transparent">
                        Filled
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    {sig.indicator && (
                      <span className="text-2xs text-muted-foreground/70">
                        via {sig.indicator}
                      </span>
                    )}
                  </div>
                </div>

                {/* Timestamp */}
                {sig.timestamp && (
                  <span className="text-2xs text-muted-foreground/60 font-mono tabular-nums flex items-center gap-1 shrink-0">
                    <Clock className="h-2.5 w-2.5" />
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
