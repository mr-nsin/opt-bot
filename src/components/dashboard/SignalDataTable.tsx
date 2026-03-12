import { memo, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatTime } from "@/lib/utils";
import { BarChart3, TrendingUp, TrendingDown } from "lucide-react";
import { trading } from "@/lib/tauri-commands";

/** Displays signal DataFrame: current + previous candle signals per stock from initial scan. */
export const SignalDataTable = memo(function SignalDataTable() {
  const signalData = useTradingStore((s) => s.signalData);
  const setSignalData = useTradingStore((s) => s.setSignalData);

  useEffect(() => {
    trading.getSignalData().then((data) => {
      if (data && Array.isArray(data.signals)) {
        setSignalData({
          signals: data.signals,
          system_started_at: data.system_started_at ?? "",
          timestamp: data.timestamp ?? new Date().toISOString(),
        });
      }
    }).catch(() => {});
  }, [setSignalData]);

  if (!signalData || !signalData.signals || signalData.signals.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
            <BarChart3 className="h-3 w-3" />
            Candle Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <BarChart3 className="h-6 w-6 text-muted-foreground/15 mb-1.5" />
            <p className="text-xs text-muted-foreground/70">No candle signals yet</p>
            <p className="text-2xs text-muted-foreground/50 mt-0.5">
              Signals appear after data feed starts and stocks are scanned
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const signals = signalData.signals;
  const systemStarted = signalData.system_started_at
    ? new Date(signalData.system_started_at).toLocaleString()
    : "—";

  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
          <BarChart3 className="h-3 w-3" />
          Candle Signals
        </CardTitle>
        <span className="text-2xs text-muted-foreground/60" title={signalData.system_started_at}>
          Started: {systemStarted}
        </span>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto max-h-[320px] overflow-y-auto">
          <table className="w-full table-pro text-xs min-w-max">
            <thead className="sticky top-0 bg-card border-b border-border/30">
              <tr className="text-muted-foreground/70 text-left">
                <th className="py-2 px-2 font-medium">Symbol</th>
                <th className="py-2 px-2 font-medium">Date</th>
                <th className="py-2 px-2 font-medium">O</th>
                <th className="py-2 px-2 font-medium">H</th>
                <th className="py-2 px-2 font-medium">L</th>
                <th className="py-2 px-2 font-medium">C</th>
                <th className="py-2 px-2 font-medium">Vol</th>
                <th className="py-2 px-2 font-medium">Signal</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((row, i) => {
                const isBuy = (row.signal || "").toUpperCase() === "BUY";
                return (
                  <tr
                    key={`${row.symbol}-${row.date}-${i}`}
                    className="border-b border-border/15 hover:bg-muted/20"
                  >
                    <td className="py-1.5 px-2 font-mono font-bold">{row.symbol}</td>
                    <td className="py-1.5 px-2 font-mono text-muted-foreground/80">
                      {row.date ? formatTime(row.date) : "—"}
                    </td>
                    <td className="py-1.5 px-2 font-mono tabular-nums">
                      ${Number(row.open ?? 0).toFixed(2)}
                    </td>
                    <td className="py-1.5 px-2 font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
                      ${Number(row.high ?? 0).toFixed(2)}
                    </td>
                    <td className="py-1.5 px-2 font-mono tabular-nums text-red-600 dark:text-red-400">
                      ${Number(row.low ?? 0).toFixed(2)}
                    </td>
                    <td className="py-1.5 px-2 font-mono tabular-nums">
                      ${Number(row.close ?? 0).toFixed(2)}
                    </td>
                    <td className="py-1.5 px-2 font-mono tabular-nums text-muted-foreground/70">
                      {Number(row.volume ?? 0).toLocaleString()}
                    </td>
                    <td className="py-1.5 px-2">
                      <Badge
                        variant={isBuy ? "success" : "danger"}
                        className="text-2xs px-1.5 py-0 h-4 flex items-center gap-0.5 w-fit"
                      >
                        {isBuy ? (
                          <TrendingUp className="h-2.5 w-2.5" />
                        ) : (
                          <TrendingDown className="h-2.5 w-2.5" />
                        )}
                        {row.signal || "NA"}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
});
