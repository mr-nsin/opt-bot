import { memo, useMemo, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface PnlPoint {
  time: string;
  pnl: number;
}

/** Maximum data points to keep in the sparkline history */
const MAX_POINTS = 120;

/**
 * PnLSparkline — An intraday P&L line chart that accumulates data points
 * from the live PnL stream. Inspired by TradingView's equity curve and
 * NinjaTrader's real-time P&L chart.
 *
 * Uses Recharts AreaChart with gradient fill for positive/negative regions.
 */
export const PnLSparkline = memo(function PnLSparkline() {
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const status = useTradingStore((s) => s.status);
  const isRunning = status === "Running";

  // Accumulate P&L history in a ref to persist across re-renders
  const historyRef = useRef<PnlPoint[]>([]);
  const lastRecordedRef = useRef<number>(0);

  // Record a new point every ~5 seconds when running
  useEffect(() => {
    if (!isRunning) return;

    const now = Date.now();
    if (now - lastRecordedRef.current < 5000) return;

    lastRecordedRef.current = now;
    const timeStr = new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "America/New_York",
    });

    historyRef.current = [
      ...historyRef.current,
      { time: timeStr, pnl: dailyPnl.total },
    ].slice(-MAX_POINTS);
  }, [dailyPnl.total, isRunning]);

  const data = historyRef.current;
  const hasData = data.length >= 2;

  const { maxPnl, minPnl } = useMemo(() => {
    if (data.length === 0) return { maxPnl: 0, minPnl: 0 };
    const values = data.map((d) => d.pnl);
    return {
      maxPnl: Math.max(...values),
      minPnl: Math.min(...values),
    };
  }, [data.length, dailyPnl.total]);

  const currentPnl = dailyPnl.total;
  const isPositive = currentPnl >= 0;

  return (
    <Card className="h-full">
      <CardHeader className="pb-0 pt-4 px-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-0.5">All Assets</p>
            <CardTitle className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary/80" />
              My Balance
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {isRunning && (
              <Badge variant="outline" className="text-xs gap-1 h-5 px-2">
                <span className="h-1 w-1 rounded-full bg-emerald-500 live-dot" />
                LIVE
              </Badge>
            )}
          </div>
        </div>

        {/* Current P&L summary */}
        <div className="flex flex-wrap items-baseline gap-2 mt-2">
          <div className="flex items-center gap-1">
            {isPositive ? (
              <TrendingUp className="h-3 w-3 text-emerald-400" />
            ) : (
              <TrendingDown className="h-3 w-3 text-red-400" />
            )}
            <span
              className={cn(
                "text-3xl font-bold font-mono tabular-nums",
                pnlColor(currentPnl),
                isPositive ? "metric-profit" : currentPnl < 0 ? "metric-loss" : ""
              )}
            >
              {formatCurrency(currentPnl)}
            </span>
          </div>
          {hasData && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>
                H <span className="font-mono tabular-nums text-emerald-500/60">{formatCurrency(maxPnl)}</span>
              </span>
              <span>
                L <span className="font-mono tabular-nums text-red-500/60">{formatCurrency(minPnl)}</span>
              </span>
            </div>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {hasData ? "Session P&L · Updates in real-time" : isRunning ? "Collecting data…" : "Start trading to see chart"}
        </p>
      </CardHeader>

      <CardContent className="pb-2 px-2">
        {!hasData ? (
          <div className="h-[130px] flex items-center justify-center">
            <div className="text-center">
              <Activity className="h-6 w-6 text-muted-foreground/25 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground/75">
                {isRunning ? "Collecting P&L data…" : "Start trading to see P&L chart"}
              </p>
            </div>
          </div>
        ) : (
          <div className="h-[130px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data}
                margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
              >
                <defs>
                  <linearGradient id="pnlGradientUp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="pnlGradientDown" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.02} />
                    <stop offset="100%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.3} />
                  </linearGradient>
                </defs>

                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground) / 0.3)" }}
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                  minTickGap={40}
                />
                <YAxis
                  domain={["dataMin - 10", "dataMax + 10"]}
                  tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground) / 0.3)" }}
                  tickLine={false}
                  axisLine={false}
                  width={45}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                />
                <ReferenceLine
                  y={0}
                  stroke="hsl(var(--border) / 0.5)"
                  strokeDasharray="3 3"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                    fontSize: "11px",
                    boxShadow: "0 4px 12px rgb(0 0 0 / 0.15)",
                  }}
                  formatter={(value: number) => [
                    formatCurrency(value),
                    "P&L",
                  ]}
                  labelStyle={{ color: "hsl(var(--muted-foreground))", fontSize: "10px" }}
                />
                <Area
                  type="monotone"
                  dataKey="pnl"
                  stroke={isPositive ? "hsl(160, 84%, 39%)" : "hsl(0, 84%, 60%)"}
                  strokeWidth={1.5}
                  fill={isPositive ? "url(#pnlGradientUp)" : "url(#pnlGradientDown)"}
                  dot={false}
                  activeDot={{
                    r: 3,
                    strokeWidth: 1,
                    fill: isPositive ? "hsl(160, 84%, 39%)" : "hsl(0, 84%, 60%)",
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
});
