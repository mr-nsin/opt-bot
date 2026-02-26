import { memo, useMemo, useRef, useEffect, useState } from "react";
import {
  Target,
  ShoppingCart,
  ShieldAlert,
  Activity,
  TrendingUp,
  TrendingDown,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Timer,
  BarChart3,
  Radio,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";

/** Trading categories that this component displays */
const TRADING_CATEGORIES = new Set(["signal", "order", "position", "risk"]);

/** Icon + color mapping for log messages based on content patterns */
function getLogDecoration(message: string, category: string, level: string) {
  const msg = message.toLowerCase();

  // Signal scanning
  if (msg.includes("scanning") || msg.includes("checking"))
    return { icon: Radio, color: "text-violet-400", bg: "bg-violet-500/5" };

  // SuperTrend flip (major signal event)
  if (msg.includes("supertrend flip") || msg.includes("signal change detected"))
    return { icon: Zap, color: "text-yellow-400", bg: "bg-yellow-500/10 border-l-2 border-l-yellow-500/50" };

  // Signal detected
  if (msg.includes("signal detected"))
    return { icon: Target, color: "text-violet-400", bg: "bg-violet-500/10 border-l-2 border-l-violet-500/50" };

  // Take profit hit
  if (msg.includes("hit take profit") || msg.includes("hit trailing"))
    return { icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10 border-l-2 border-l-emerald-500/50" };

  // Stop loss hit
  if (msg.includes("hit stop loss"))
    return { icon: XCircle, color: "text-red-400", bg: "bg-red-500/10 border-l-2 border-l-red-500/50" };

  // Order placed / entry / exit filled
  if (msg.includes("order placed") || msg.includes("entry filled"))
    return { icon: ShoppingCart, color: "text-emerald-400", bg: "bg-emerald-500/8" };
  if (msg.includes("exit filled"))
    return { icon: ShoppingCart, color: "text-blue-400", bg: "bg-blue-500/8" };

  // Order rejected / cancelled
  if (msg.includes("rejected"))
    return { icon: XCircle, color: "text-red-400", bg: "bg-red-500/8" };
  if (msg.includes("cancelled") || msg.includes("expired"))
    return { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/5" };

  // Trailing profit updates
  if (msg.includes("tp trail") || msg.includes("tp trigger"))
    return { icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/5" };

  // Closing position
  if (msg.includes("closing:"))
    return { icon: Activity, color: "text-blue-400", bg: "bg-blue-500/5" };

  // Cooldown active
  if (msg.includes("cooldown"))
    return { icon: Timer, color: "text-amber-400", bg: "" };

  // Day limit / risk
  if (msg.includes("day lock") || msg.includes("day limit") || msg.includes("market hours ended"))
    return { icon: ShieldAlert, color: "text-red-400", bg: "bg-red-500/10 border-l-2 border-l-red-500/30" };

  // ATR / delta / volume checks
  if (msg.includes("atr=") || msg.includes("delta=") || msg.includes("vol="))
    return { icon: BarChart3, color: "text-cyan-400", bg: "" };

  // Position already open / order exists
  if (msg.includes("position already") || msg.includes("pending") || msg.includes("skipping"))
    return { icon: Activity, color: "text-muted-foreground/60", bg: "" };

  // No signal (low priority)
  if (msg.includes("no signal"))
    return { icon: Radio, color: "text-muted-foreground/30", bg: "" };

  // Default per category
  if (category === "signal")
    return { icon: Target, color: "text-violet-400", bg: "" };
  if (category === "order")
    return { icon: ShoppingCart, color: "text-emerald-400", bg: "" };
  if (category === "position")
    return { icon: Activity, color: "text-cyan-400", bg: "" };
  if (category === "risk")
    return { icon: ShieldAlert, color: "text-amber-400", bg: "" };

  return { icon: Zap, color: "text-muted-foreground/50", bg: "" };
}

/** Extracts symbol from a log message like "SPY CALL: ..." or "SPY 585C..." */
function extractSymbol(msg: string): string | null {
  const match = msg.match(/^(\b[A-Z]{1,5}\b)/);
  return match ? match[1] : null;
}

/** Formats a timestamp to HH:MM:SS */
function formatTs(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "";
  }
}

/**
 * EngineActivity — A real-time feed of trading engine activity.
 * Filters logs to show only signal/order/position/risk categories,
 * with rich icons and highlighting based on log content.
 */
export const EngineActivity = memo(function EngineActivity() {
  const logs = useLogStore((s) => s.logs);
  const status = useTradingStore((s) => s.status);
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);
  const isRunning = status === "Running";
  const feedRef = useRef<HTMLDivElement>(null);
  const [showDebug, setShowDebug] = useState(false);

  // Filter to only trading-relevant logs
  const tradingLogs = useMemo(() => {
    return logs
      .filter((l) => {
        if (!TRADING_CATEGORIES.has(l.category?.toLowerCase())) return false;
        if (!showDebug && l.level === "DEBUG") return false;
        return true;
      })
      .slice(-50); // Show last 50 trading logs
  }, [logs, showDebug]);

  // Counts by category
  const counts = useMemo(() => {
    const c = { signal: 0, order: 0, position: 0, risk: 0 };
    for (const l of logs) {
      const cat = l.category?.toLowerCase() as keyof typeof c;
      if (cat in c) c[cat]++;
    }
    return c;
  }, [logs]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [tradingLogs.length]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
            <Activity className="h-3 w-3 text-cyan-400/70" />
            Engine Activity
            {isRunning && isSignalScanning && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
            )}
            {isRunning && !isSignalScanning && (
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500 animate-pulse" />
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-1.5">
            {counts.signal > 0 && (
              <Badge variant="outline" className="text-2xs gap-1 text-violet-400">
                <Target className="h-2.5 w-2.5" />
                {counts.signal}
              </Badge>
            )}
            {counts.order > 0 && (
              <Badge variant="outline" className="text-2xs gap-1 text-emerald-400">
                <ShoppingCart className="h-2.5 w-2.5" />
                {counts.order}
              </Badge>
            )}
            <button
              onClick={() => setShowDebug(!showDebug)}
              className={cn(
                "text-2xs px-1.5 py-0.5 rounded border transition-colors",
                showDebug
                  ? "border-violet-500/30 bg-violet-500/10 text-violet-400"
                  : "border-border/30 text-muted-foreground/40 hover:text-muted-foreground"
              )}
            >
              Verbose
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {tradingLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center px-4">
            <Radio className="h-6 w-6 text-muted-foreground/15 mb-1.5" />
            <p className="text-[11px] text-muted-foreground/50">
              {isRunning ? "Waiting for activity…" : "Engine not running"}
            </p>
            <p className="text-[9px] text-muted-foreground/30 mt-0.5">
              {isRunning
                ? "Signal scans, orders, and risk alerts appear here"
                : "Start trading to see engine activity"}
            </p>
          </div>
        ) : (
          <div
            ref={feedRef}
            className="max-h-[300px] overflow-y-auto font-mono text-[10px]"
          >
            {tradingLogs.map((l, i) => {
              const dec = getLogDecoration(l.message, l.category?.toLowerCase() || "", l.level);
              const Icon = dec.icon;
              const symbol = extractSymbol(l.message);
              const isNew = i >= tradingLogs.length - 3;

              return (
                <div
                  key={`${l.timestamp}-${i}`}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 border-b border-border/8 transition-colors hover:bg-muted/15",
                    dec.bg,
                    isNew && l.level !== "DEBUG" && "animate-fade-up"
                  )}
                >
                  {/* Icon */}
                  <div className={cn("shrink-0", dec.color)}>
                    <Icon className="h-2.5 w-2.5" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 truncate">
                    <span className="flex items-center gap-1">
                      {symbol && (
                        <span className="font-bold text-foreground/85 text-[10px]">
                          {symbol}
                        </span>
                      )}
                      <span
                        className={cn(
                          "text-foreground/60 truncate",
                          l.level === "DEBUG" && "text-muted-foreground/40",
                          l.level === "ERROR" && "text-red-400/80",
                          l.level === "WARN" && "text-amber-400/70"
                        )}
                      >
                        {symbol ? l.message.replace(new RegExp(`^${symbol}\\s*`), "") : l.message}
                      </span>
                    </span>
                  </div>

                  {/* Timestamp */}
                  <span className="text-muted-foreground/25 shrink-0 tabular-nums text-[9px]">
                    {formatTs(l.timestamp)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
