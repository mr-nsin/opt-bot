import { memo, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, formatTime, pnlColor } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown, ClipboardList } from "lucide-react";

type SortField = "time" | "symbol" | "pnl" | "side";
type SortDir = "asc" | "desc";

export const TradeBlotter = memo(function TradeBlotter() {
  const todayTrades = useTradingStore((s) => s.todayTrades);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);

  const [sortField, setSortField] = useState<SortField>("time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const sorted = useMemo(() => {
    return [...todayTrades].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "time":
          cmp = ((a.timestamp as string) ?? "").localeCompare((b.timestamp as string) ?? "");
          break;
        case "symbol":
          cmp = ((a.symbol as string) ?? "").localeCompare((b.symbol as string) ?? "");
          break;
        case "pnl":
          cmp = ((a.pnl as number) ?? 0) - ((b.pnl as number) ?? 0);
          break;
        case "side":
          cmp = ((a.side as string) ?? "").localeCompare((b.side as string) ?? "");
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [todayTrades, sortField, sortDir]);

  const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : "0.0";

  return (
    <Card>
      <CardHeader className="py-2 px-3 flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
          <ClipboardList className="h-3 w-3" />
          Trade Blotter
        </CardTitle>
        <div className="flex items-center gap-2">
          {totalTrades > 0 && (
            <span className="text-xs text-muted-foreground font-mono tabular-nums">
              {totalTrades} trades · {winRate}% win · W{winningTrades}/L{losingTrades}
            </span>
          )}
          <Badge variant={todayTrades.length > 0 ? "success" : "secondary"} className="text-xs h-5 px-2">
            {todayTrades.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {todayTrades.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8">
            <ClipboardList className="h-6 w-6 text-muted-foreground/10 mb-1.5" />
            <p className="text-sm text-muted-foreground/70">No trades executed today</p>
            <p className="text-xs text-muted-foreground/50 mt-0.5">
              Trades appear here as orders are filled
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-pro">
              <thead>
                <tr>
                  <SortTh field="time" label="Time" sort={sortField} dir={sortDir} onClick={toggleSort} />
                  <SortTh field="symbol" label="Symbol" sort={sortField} dir={sortDir} onClick={toggleSort} />
                  <th>Type</th>
                  <th>Strike</th>
                  <th>Expiry</th>
                  <SortTh field="side" label="Side" sort={sortField} dir={sortDir} onClick={toggleSort} />
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <SortTh field="pnl" label="P&L" sort={sortField} dir={sortDir} onClick={toggleSort} />
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((t, i) => {
                  const pnl = (t.pnl as number) ?? 0;
                  const status = (t.status as string) ?? "open";
                  const isClosed = status === "closed";
                  return (
                    <tr key={`${t.id}-${i}`} className="transition-colors">
                      <td className="text-muted-foreground/70 font-mono tabular-nums text-xs">
                        {t.timestamp ? formatTime(t.timestamp as string) : "—"}
                      </td>
                      <td className="font-mono font-bold text-xs">{t.symbol}</td>
                      <td>
                        <Badge
                          variant={(t.right as string) === "CALL" || (t.right as string) === "C" ? "success" : "danger"}
                          className="text-xs font-bold px-1.5 py-0"
                        >
                          {(t.right as string) === "C" || (t.right as string) === "CALL" ? "CALL" : "PUT"}
                        </Badge>
                      </td>
                      <td className="font-mono tabular-nums text-xs">
                        ${Number(t.strike ?? 0).toFixed(1)}
                      </td>
                      <td className="text-muted-foreground/70 text-xs">{t.expiry as string}</td>
                      <td>
                        <Badge
                          variant={(t.side as string) === "BUY" ? "success" : "danger"}
                          className="text-xs px-1.5 py-0"
                        >
                          {t.side as string}
                        </Badge>
                      </td>
                      <td className="font-mono tabular-nums text-xs">{t.quantity as number}</td>
                      <td className="font-mono tabular-nums text-xs">
                        ${Number(t.entry_price ?? 0).toFixed(2)}
                      </td>
                      <td className="font-mono tabular-nums text-xs">
                        {isClosed ? `$${Number(t.exit_price ?? 0).toFixed(2)}` : "—"}
                      </td>
                      <td>
                        {isClosed ? (
                          <span className={cn("font-mono font-bold tabular-nums text-xs", pnlColor(pnl))}>
                            {formatCurrency(pnl)}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground/50">—</span>
                        )}
                      </td>
                      <td>
                        <Badge
                          variant={isClosed ? (pnl >= 0 ? "success" : "danger") : "secondary"}
                          className="text-xs px-1.5 py-0"
                        >
                          {isClosed ? (pnl >= 0 ? "WIN" : "LOSS") : "OPEN"}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

function SortTh({
  field,
  label,
  sort,
  dir,
  onClick,
}: {
  field: SortField;
  label: string;
  sort: SortField;
  dir: SortDir;
  onClick: (f: SortField) => void;
}) {
  const isActive = sort === field;
  return (
    <th
      className={cn(
        "cursor-pointer select-none transition-colors",
        isActive ? "!text-primary" : "hover:!text-foreground/70"
      )}
      onClick={() => onClick(field)}
    >
      <div className="flex items-center gap-0.5">
        {label}
        {isActive ? (
          dir === "asc" ? <ArrowUp className="h-2.5 w-2.5" /> : <ArrowDown className="h-2.5 w-2.5" />
        ) : (
          <ArrowUpDown className="h-2.5 w-2.5 opacity-30" />
        )}
      </div>
    </th>
  );
}
