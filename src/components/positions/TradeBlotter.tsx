import React, { memo, useMemo, useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/stores/tradingStore";
import { usePositionStore, positionKey } from "@/stores/positionStore";
import { cn, formatCurrency, formatTime, pnlColor } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown, ClipboardList, Clock, Tag, Target, Calendar, Hash, BarChart3, DollarSign, CheckCircle } from "lucide-react";
import type { Position } from "@/lib/types";

type SortField = "time" | "symbol" | "pnl" | "side";
type SortDir = "asc" | "desc";

import { useVirtualizer } from "@tanstack/react-virtual";

/** Normalize option right for matching: "CALL" → "C", "PUT" → "P" */
const nrFn = (r?: string) => (r === "CALL" ? "C" : r === "PUT" ? "P" : r);
const normExp = (e?: string) => (e || "").replace(/-/g, "").replace(/\s/g, "").trim();

export const TradeBlotter = memo(function TradeBlotter() {
  const todayTrades = useTradingStore((s) => s.todayTrades);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);

  // Throttled subscription: read positions at most every 500ms to avoid re-render storms
  const rawPositions = usePositionStore((s) => s.positions);
  const [positions, setPositions] = useState(rawPositions);
  const throttleRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (throttleRef.current != null) return;
    setPositions(rawPositions);
    throttleRef.current = setTimeout(() => {
      throttleRef.current = null;
      setPositions(usePositionStore.getState().positions);
    }, 500);
  }, [rawPositions]);

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

  // Build a lookup from positionStore for O(1) access by key
  const positionMap = useMemo(() => {
    const map = new Map<string, Position>();
    for (const p of positions) {
      const key = positionKey(p.symbol, p.strike, p.right, p.expiry);
      map.set(key, p);
    }
    return map;
  }, [positions]);

  // Enrich today's trades with live data from positionStore
  const enrichedTrades = useMemo(() => {
    return todayTrades.map((t) => {
      const status = (t.status as string) ?? "open";
      const isOpen = status === "open" || status === "";
      if (!isOpen) return t; // Closed trades already have final P&L

      // Look up matching position to get live current_price, bid, ask, pnl
      const key = positionKey(
        (t.symbol as string) || "",
        t.strike as number | undefined,
        t.right as string | undefined,
        t.expiry as string | undefined,
      );
      const livePos = positionMap.get(key);
      if (!livePos) return t;

      return {
        ...t,
        _live_current_price: livePos.current_price,
        _live_bid: livePos.bid,
        _live_ask: livePos.ask,
        _live_pnl: livePos.pnl,
        _live_pnl_percent: livePos.pnl_percent,
      };
    });
  }, [todayTrades, positionMap]);

  const sorted = useMemo(() => {
    return [...enrichedTrades].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "time":
          cmp = ((a.timestamp as string) ?? "").localeCompare((b.timestamp as string) ?? "");
          break;
        case "symbol":
          cmp = ((a.symbol as string) ?? "").localeCompare((b.symbol as string) ?? "");
          break;
        case "pnl": {
          const aPnl = (a as any)._live_pnl ?? a.pnl ?? 0;
          const bPnl = (b as any)._live_pnl ?? b.pnl ?? 0;
          cmp = aPnl - bPnl;
          break;
        }
        case "side":
          cmp = ((a.side as string) ?? "").localeCompare((b.side as string) ?? "");
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [enrichedTrades, sortField, sortDir]);

  const winRate = closedTrades > 0 ? ((winningTrades / closedTrades) * 100).toFixed(1) : "0.0";

  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: sorted.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 10,
  });

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
        <div ref={parentRef} className="overflow-x-auto overflow-y-auto min-w-0 max-h-[500px]">
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
                <th className="text-right" title="Entry / Exit price (live current price for open trades)">
                  <span className="flex items-center justify-end gap-1">
                    <BarChart3 className="h-3 w-3 opacity-60" />
                    Entry / Current
                  </span>
                </th>
                <th className="text-right" title="Bid / Ask for open trades">
                  <span className="flex items-center justify-end gap-1">
                    <BarChart3 className="h-3 w-3 opacity-60" />
                    Bid / Ask
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
              {todayTrades.length === 0 ? (
                <tr>
                  <td colSpan={11}>
                    <div className="flex flex-col items-center justify-center py-8">
                      <ClipboardList className="h-6 w-6 text-muted-foreground/10 mb-1.5" />
                      <p className="text-sm text-muted-foreground/70">No trades executed today</p>
                      <p className="text-xs text-muted-foreground/50 mt-0.5">
                        Trades appear here as orders are filled
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                <>
                {rowVirtualizer.getVirtualItems().length > 0 && (
                  <tr>
                    <td colSpan={11} style={{ height: `${rowVirtualizer.getVirtualItems()[0]?.start || 0}px` }} />
                  </tr>
                )}
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const t = sorted[virtualRow.index];
                  const i = virtualRow.index;
                  const status = (t.status as string) ?? "open";
                  const isClosed = status === "closed";
                  const isOpen = !isClosed;

                  // Live data from positionStore (only for open trades)
                  const livePnl = (t as any)._live_pnl as number | undefined;
                  const liveCurrentPrice = (t as any)._live_current_price as number | undefined;
                  const liveBid = (t as any)._live_bid as number | undefined;
                  const liveAsk = (t as any)._live_ask as number | undefined;
                  const livePnlPct = (t as any)._live_pnl_percent as number | undefined;

                  // Resolve P&L: live for open trades, final for closed
                  const displayPnl = isClosed
                    ? (t.pnl as number | undefined)
                    : livePnl;
                  const pnlKnown = displayPnl !== undefined && displayPnl !== null;

                  // Resolve current / exit price
                  const displayCurrentPrice = isClosed
                    ? (t.exit_price as number | undefined)
                    : liveCurrentPrice;

                  return (
                    <tr 
                      key={`${t.id}-${i}`} 
                      className="transition-colors" 
                      ref={rowVirtualizer.measureElement}
                      data-index={virtualRow.index}
                    >
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

                      {/* Entry / Current Price */}
                      <td className="text-xs font-mono tabular-nums text-right">
                        <span className="flex flex-col gap-0.5 items-end">
                          <span className="text-muted-foreground/70" title="Entry price">
                            <span className="text-[10px] uppercase text-muted-foreground/50 mr-0.5">Entry</span>
                            ${Number(t.entry_price ?? 0).toFixed(2)}
                          </span>
                          <span
                            className={cn(
                              "font-medium",
                              isOpen && liveCurrentPrice != null && liveCurrentPrice > 0
                                ? "text-foreground/90"
                                : "text-muted-foreground/80"
                            )}
                            title={isClosed ? "Exit price" : "Live current price"}
                          >
                            <span className="text-[10px] uppercase text-muted-foreground/50 mr-0.5">
                              {isClosed ? "Exit" : "Now"}
                            </span>
                            {displayCurrentPrice != null && displayCurrentPrice > 0
                              ? `$${Number(displayCurrentPrice).toFixed(2)}`
                              : "—"}
                          </span>
                        </span>
                      </td>

                      {/* Bid / Ask */}
                      <td className="text-xs font-mono tabular-nums text-right">
                        {isOpen && (liveBid != null && liveBid > 0 || liveAsk != null && liveAsk > 0) ? (
                          <span className="flex flex-col gap-0.5 items-end">
                            {liveBid != null && liveBid > 0 && (
                              <span title="Bid">${Number(liveBid).toFixed(2)}</span>
                            )}
                            {liveAsk != null && liveAsk > 0 && (
                              <span className="text-muted-foreground/80" title="Ask">
                                ${Number(liveAsk).toFixed(2)}
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="text-muted-foreground/40">—</span>
                        )}
                      </td>

                      {/* P&L */}
                      <td className="text-right">
                        {pnlKnown ? (
                          <div className="flex flex-col items-end gap-0.5">
                            <span className={cn("font-mono font-bold tabular-nums text-xs", pnlColor(displayPnl))}>
                              {formatCurrency(displayPnl)}
                            </span>
                            {isOpen && livePnlPct != null && (
                              <span className={cn("text-[10px] font-mono tabular-nums opacity-60", pnlColor(displayPnl))}>
                                ({livePnlPct >= 0 ? "+" : ""}{livePnlPct.toFixed(1)}%)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground/50">—</span>
                        )}
                      </td>

                      {/* Status */}
                      <td>
                        <Badge
                          variant={
                            isClosed
                              ? pnlKnown
                                ? displayPnl! > 0
                                  ? "success"
                                  : displayPnl! < 0
                                    ? "danger"
                                    : "secondary"
                                : "secondary"
                              : pnlKnown
                                ? displayPnl! > 0
                                  ? "success"
                                  : displayPnl! < 0
                                    ? "danger"
                                    : "secondary"
                                : "secondary"
                          }
                          className="text-xs px-1.5 py-0"
                        >
                          {isClosed
                            ? pnlKnown
                              ? displayPnl! > 0
                                ? "WIN"
                                : displayPnl! < 0
                                  ? "LOSS"
                                  : "BE"
                              : "CLOSED"
                            : "OPEN"}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
                {rowVirtualizer.getVirtualItems().length > 0 && (
                  <tr>
                    <td colSpan={11} style={{ height: `${rowVirtualizer.getTotalSize() - (rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1]?.end || 0)}px` }} />
                  </tr>
                )}
                </>
              )}
            </tbody>
          </table>
        </div>
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
