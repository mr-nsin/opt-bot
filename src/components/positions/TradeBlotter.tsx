import React, { memo, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, formatTime, pnlColor } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown, ClipboardList, Clock, Tag, Target, Calendar, Hash, BarChart3, DollarSign, CheckCircle } from "lucide-react";

type SortField = "time" | "symbol" | "pnl" | "side";
type SortDir = "asc" | "desc";

export const TradeBlotter = memo(function TradeBlotter() {
  const todayTrades = useTradingStore((s) => s.todayTrades);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
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

  const winRate = closedTrades > 0 ? ((winningTrades / closedTrades) * 100).toFixed(1) : "0.0";

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
              {openTrades} open / {closedTrades} closed · {winRate}% win · W{winningTrades}/L{losingTrades}
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
          <div className="overflow-x-auto min-w-0">
            <table className="w-full table-pro min-w-max">
              <thead>
                <tr>
                  <SortTh field="time" label="Time" sort={sortField} dir={sortDir} onClick={toggleSort} align="left" icon={Clock} />
                  <SortTh field="symbol" label="Symbol" sort={sortField} dir={sortDir} onClick={toggleSort} align="left" icon={Tag} />
                  <th className="text-center">
                    <span className="flex items-center justify-center gap-1">
                      <ClipboardList className="h-3 w-3 opacity-60" />
                      Type
                    </span>
                  </th>
                  <th className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Target className="h-3 w-3 opacity-60" />
                      Strike
                    </span>
                  </th>
                  <th className="text-left">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 opacity-60" />
                      Expiry
                    </span>
                  </th>
                  <SortTh field="side" label="Side" sort={sortField} dir={sortDir} onClick={toggleSort} align="left" />
                  <th className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Hash className="h-3 w-3 opacity-60" />
                      Qty
                    </span>
                  </th>
                  <th className="text-right" title="Entry / Exit price">
                    <span className="flex items-center justify-end gap-1">
                      <BarChart3 className="h-3 w-3 opacity-60" />
                      Entry / Exit
                    </span>
                  </th>
                  <SortTh field="pnl" label="P&L" sort={sortField} dir={sortDir} onClick={toggleSort} align="right" icon={DollarSign} />
                  <th className="text-left">
                    <span className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 opacity-60" />
                      Status
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((t, i) => {
                  const pnl = t.pnl as number | undefined;
                  const pnlKnown = pnl !== undefined && pnl !== null;
                  const status = (t.status as string) ?? "open";
                  const isClosed = status === "closed";
                  return (
                    <tr key={`${t.id}-${i}`} className="transition-colors">
                      <td className="text-muted-foreground/70 font-mono tabular-nums text-xs">
                        {t.timestamp ? formatTime(t.timestamp as string) : "—"}
                      </td>
                      <td className="font-mono font-bold text-xs">{t.symbol}</td>
                      <td className="text-center">
                        <Badge
                          variant={(t.right as string) === "CALL" || (t.right as string) === "C" ? "success" : "danger"}
                          className="text-xs font-bold px-1.5 py-0"
                        >
                          {(t.right as string) === "C" || (t.right as string) === "CALL" ? "CALL" : "PUT"}
                        </Badge>
                      </td>
                      <td className="font-mono tabular-nums text-xs text-right">
                        ${Number(t.strike ?? 0).toFixed(1)}
                      </td>
                      <td className="text-muted-foreground/70 text-xs">{t.expiry as string}</td>
                      <td className="text-center">
                        <Badge
                          variant={(t.side as string) === "BUY" ? "success" : "danger"}
                          className="text-xs px-1.5 py-0"
                        >
                          {t.side as string}
                        </Badge>
                      </td>
                      <td className="font-mono tabular-nums text-xs text-right">{t.quantity as number}</td>
                      <td className="text-xs font-mono tabular-nums text-right">
                        <span className="flex flex-col gap-0.5 items-end">
                          <span className="text-muted-foreground/80" title="Entry price">
                            ${Number(t.entry_price ?? 0).toFixed(2)}
                          </span>
                          <span title="Exit price">
                            {isClosed && t.exit_price != null
                              ? `$${Number(t.exit_price).toFixed(2)}`
                              : "—"}
                          </span>
                        </span>
                      </td>
                      <td className="text-right">
                        {isClosed ? (
                          pnlKnown ? (
                            <span className={cn("font-mono font-bold tabular-nums text-xs", pnlColor(pnl))}>
                              {formatCurrency(pnl)}
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground/50">—</span>
                          )
                        ) : (
                          <span className="text-xs text-muted-foreground/50">—</span>
                        )}
                      </td>
                      <td>
                        <Badge
                          variant={
                            isClosed
                              ? pnlKnown
                                ? pnl > 0
                                  ? "success"
                                  : pnl < 0
                                    ? "danger"
                                    : "secondary"
                                : "secondary"
                              : "secondary"
                          }
                          className="text-xs px-1.5 py-0"
                        >
                          {isClosed
                            ? pnlKnown
                              ? pnl > 0
                                ? "WIN"
                                : pnl < 0
                                  ? "LOSS"
                                  : "BE"
                              : "CLOSED"
                            : "OPEN"}
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
  align = "left",
  icon: Icon,
}: {
  field: SortField;
  label: string;
  sort: SortField;
  dir: SortDir;
  onClick: (f: SortField) => void;
  align?: "left" | "right";
  icon?: React.ComponentType<{ className?: string }>;
}) {
  const isActive = sort === field;
  return (
    <th
      className={cn(
        "cursor-pointer select-none transition-colors",
        align === "right" ? "text-right" : "text-left",
        isActive ? "!text-primary" : "hover:!text-foreground/70"
      )}
      onClick={() => onClick(field)}
    >
      <div className={cn("flex items-center gap-1", align === "right" && "justify-end")}>
        {Icon && <Icon className="h-3 w-3 opacity-60 shrink-0" />}
        <span className="flex items-center gap-0.5">
          {label}
          {isActive ? (
            dir === "asc" ? <ArrowUp className="h-2.5 w-2.5" /> : <ArrowDown className="h-2.5 w-2.5" />
          ) : (
            <ArrowUpDown className="h-2.5 w-2.5 opacity-30" />
          )}
        </span>
      </div>
    </th>
  );
}
