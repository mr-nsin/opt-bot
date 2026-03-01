import { Radio, Database, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn } from "@/lib/utils";

/** Shows what data is being fetched (updated every ~10s when engine is running). */
export function DataFeedStatus() {
  const { dataStatus } = useTradingStore();

  if (!dataStatus) {
    return (
      <Card className="h-full flex flex-col">
        <CardHeader className="shrink-0">
          <CardTitle className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Database className="h-5 w-5 text-primary/80" />
            Data feed
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0">
          <p className="text-sm text-muted-foreground">
            Start trading to see live data status (updates every 10s).
          </p>
        </CardContent>
      </Card>
    );
  }

  const { connected, data_feed_started, symbols, event_queue_size, tick_subscriptions, stock_ticks_sample, history_bars_count, timestamp } = dataStatus;
  const updated = timestamp ? new Date(timestamp).toLocaleTimeString() : "—";

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 shrink-0">
        <CardTitle className="text-2xl font-bold tracking-tight text-foreground flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary/80" />
            Data feed
          </span>
          <span className="text-sm font-medium text-muted-foreground">updated {updated}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 flex-1 flex flex-col min-h-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={connected ? "success" : "secondary"} className="gap-1">
            <Radio className="h-3 w-3" />
            TWS {connected ? "Connected" : "Disconnected"}
          </Badge>
          <Badge variant={data_feed_started ? "success" : "secondary"} className="gap-1">
            <Activity className="h-3 w-3" />
            Feed {data_feed_started ? "On" : "Off"}
          </Badge>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
          <div>
            <span className="text-sm font-medium text-muted-foreground">Symbols</span>
            <p className="font-medium tabular-nums">{symbols.length}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-muted-foreground">Queue</span>
            <p className="font-medium tabular-nums">{event_queue_size}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-muted-foreground">Ticks</span>
            <p className="font-medium tabular-nums">{tick_subscriptions}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-muted-foreground">Bars</span>
            <p className="font-medium tabular-nums">{history_bars_count}</p>
          </div>
        </div>
        {stock_ticks_sample.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-muted-foreground mb-1.5">STK last (sample)</p>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {stock_ticks_sample.slice(0, 12).map((t) => (
                <span key={t.symbol} className={cn("font-mono tabular-nums", data_feed_started && "text-emerald-600 dark:text-emerald-400")}>
                  {t.symbol}={t.last}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
