import { useEffect, useState, useMemo, memo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PositionRow } from "./PositionRow";
import { PositionHistory } from "./PositionHistory";
import { TradeBlotter } from "./TradeBlotter";
import { usePositions } from "@/hooks/usePositions";
import { useTradingEngine } from "@/hooks/useTradingEngine";
import { useTradingStore } from "@/stores/tradingStore";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RefreshCw,
  XCircle,
  Briefcase,
  TrendingUp,
  TrendingDown,
  Target,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Tag,
  Calendar,
  Hash,
  BarChart3,
  LineChart,
  Shield,
  DollarSign,
} from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import type { Position } from "@/lib/types";

type SortField = "symbol" | "pnl" | "strike" | "qty";
type SortDir = "asc" | "desc";

export const PositionsPage = memo(function PositionsPage() {
  const { positions, closedPositions, loading, refreshPositions, closeAll, closeCalls, closePuts } = usePositions();
  const { refreshStatus } = useTradingEngine();
  const todayTrades = useTradingStore((s) => s.todayTrades);
  const [showCloseAll, setShowCloseAll] = useState(false);
  const [showCloseCalls, setShowCloseCalls] = useState(false);
  const [showClosePuts, setShowClosePuts] = useState(false);
  const [sortField, setSortField] = useState<SortField>("pnl");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    // Fetch once on mount; live updates come via position_update events (every 2s from engine)
    Promise.all([refreshPositions(), refreshStatus()]);
  }, [refreshPositions, refreshStatus]);

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortDir("desc");
      }
    },
    [sortField]
  );

  const sortedPositions = useMemo(() => {
    const sorted = [...positions].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "symbol":
          cmp = (a.symbol ?? "").localeCompare(b.symbol ?? "");
          break;
        case "pnl":
          cmp = (a.pnl ?? 0) - (b.pnl ?? 0);
          break;
        case "strike":
          cmp = (a.strike ?? 0) - (b.strike ?? 0);
          break;
        case "qty":
          cmp = (a.quantity ?? 0) - (b.quantity ?? 0);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [positions, sortField, sortDir]);

  const summary = useMemo(() => {
    const totalPnl = positions.reduce((s, p) => s + (p.pnl ?? 0), 0);
    const callCount = positions.filter((p) => p.right === "C" || p.right === "CALL").length;
    const putCount = positions.filter((p) => p.right === "P" || p.right === "PUT").length;
    return { totalPnl, callCount, putCount };
  }, [positions]);

  // Merge closedPositions (from trade_closed events) with todayTrades closed (from backend hydration)
  const closedForHistory = useMemo(() => {
    const fromEvents = closedPositions;
    const fromTrades = todayTrades
      .filter((t) => (t.status as string) === "closed")
      .map((t) => ({
        symbol: t.symbol ?? "",
        strike: t.strike ?? 0,
        right: t.right ?? "",
        expiry: t.expiry ?? "",
        quantity: t.quantity ?? 0,
        avg_price: t.entry_price,
        entry_price: t.entry_price,
        exit_price: t.exit_price,
        pnl: t.pnl,
        timestamp: t.timestamp,
      }));
    const seen = new Set<string>();
    const merged: typeof fromEvents = [];
    for (const p of [...fromEvents, ...fromTrades]) {
      const key = `${p.symbol}-${p.strike}-${p.right}-${(p.expiry ?? "").replace(/-/g, "")}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(p);
      }
    }
    return merged.sort((a, b) => {
      const ta = (a.timestamp as string) ?? "";
      const tb = (b.timestamp as string) ?? "";
      return tb.localeCompare(ta);
    });
  }, [closedPositions, todayTrades]);

  return (
    <div className="space-y-2.5 min-w-0 w-full">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary/80" />
            Positions
          </h2>
          <p className="text-xs text-muted-foreground/60">Active and closed positions</p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <Button variant="outline" size="sm" onClick={refreshPositions} disabled={loading} className="h-8 text-xs">
            <RefreshCw className={`h-3 w-3 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          {summary.callCount > 0 && (
            <Button variant="outline" size="sm" onClick={() => setShowCloseCalls(true)} className="h-8 text-xs border-emerald-500/50 text-emerald-600 hover:bg-emerald-500/10">
              <TrendingUp className="h-3 w-3 mr-1" /> Close Calls ({summary.callCount})
            </Button>
          )}
          {summary.putCount > 0 && (
            <Button variant="outline" size="sm" onClick={() => setShowClosePuts(true)} className="h-8 text-xs border-red-500/50 text-red-600 hover:bg-red-500/10">
              <TrendingDown className="h-3 w-3 mr-1" /> Close Puts ({summary.putCount})
            </Button>
          )}
          {positions.length > 0 && (
            <Button variant="destructive" size="sm" onClick={() => setShowCloseAll(true)} className="h-8 text-xs">
              <XCircle className="h-3 w-3 mr-1" /> Close All
            </Button>
          )}
        </div>
      </div>

      {/* Position summary row */}
      {positions.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          <MiniStat
            icon={Target}
            iconColor="text-muted-foreground/60"
            label="Active"
            value={String(positions.length)}
          />
          <MiniStat
            icon={summary.totalPnl >= 0 ? TrendingUp : TrendingDown}
            iconColor={summary.totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}
            label="Total P&L"
            value={formatCurrency(summary.totalPnl)}
            valueColor={pnlColor(summary.totalPnl)}
          />
          <MiniStat
            icon={TrendingUp}
            iconColor="text-emerald-400"
            label="Calls"
            value={String(summary.callCount)}
          />
          <MiniStat
            icon={TrendingDown}
            iconColor="text-red-400"
            label="Puts"
            value={String(summary.putCount)}
          />
        </div>
      )}

      {/* Positions table */}
      <Card>
        <CardHeader className="py-2 px-3 flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
            <Briefcase className="h-3 w-3" />
            Active Positions
          </CardTitle>
          <Badge variant={positions.length > 0 ? "success" : "secondary"} className="text-xs h-5 px-2">
            {positions.length}
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {loading && positions.length === 0 ? (
            <div className="space-y-1 p-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full rounded-md" />
              ))}
            </div>
          ) : positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8">
              <Briefcase className="h-6 w-6 text-muted-foreground/10 mb-1.5" />
              <p className="text-sm text-muted-foreground/70">No active positions</p>
              <p className="text-xs text-muted-foreground/50 mt-0.5">
                Positions appear when trades are executed
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto min-w-0">
              <table className="w-full table-pro min-w-max">
                <thead>
                  <tr>
                    <th className="w-6" />
                    <SortTh field="symbol" label="Symbol" sort={sortField} dir={sortDir} onClick={toggleSort} align="left" icon={Tag} />
                    <th className="text-center">
                      <span className="flex items-center justify-center gap-1">
                        <Briefcase className="h-3 w-3 opacity-60" />
                        Type
                      </span>
                    </th>
                    <SortTh field="strike" label="Strike" sort={sortField} dir={sortDir} onClick={toggleSort} align="right" icon={Target} />
                    <th className="text-left">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 opacity-60" />
                        Expiry
                      </span>
                    </th>
                    <SortTh field="qty" label="Qty" sort={sortField} dir={sortDir} onClick={toggleSort} align="right" icon={Hash} />
                    <th className="text-right" title="Entry (avg) / Current price">
                      <span className="flex items-center justify-end gap-1">
                        <BarChart3 className="h-3 w-3 opacity-60" />
                        Entry / Current
                      </span>
                    </th>
                    <th className="text-right text-muted-foreground/70 font-normal" title="Bid / Ask prices used for TP/SL">
                      <span className="flex items-center justify-end gap-1">
                        <LineChart className="h-3 w-3 opacity-60" />
                        Bid / Ask
                      </span>
                    </th>
                    <th className="text-right text-muted-foreground/70 font-normal">
                      <span className="flex items-center justify-end gap-1">
                        <Shield className="h-3 w-3 opacity-60" />
                        TP / SL
                      </span>
                    </th>
                    <SortTh field="pnl" label="P&L" sort={sortField} dir={sortDir} onClick={toggleSort} align="right" icon={DollarSign} />
                    <th className="w-16 text-right" />
                  </tr>
                </thead>
                <tbody>
                  {sortedPositions.map((p) => (
                    <PositionRow key={`${p.symbol}-${p.strike}-${p.right}`} position={p} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <TradeBlotter />

      <PositionHistory positions={closedForHistory} />

      <ConfirmDialog
        open={showCloseAll}
        title="Close All Positions"
        message={`Close all ${positions.length} active position(s)?`}
        confirmLabel="Close All"
        variant="destructive"
        onConfirm={() => { setShowCloseAll(false); closeAll(); }}
        onCancel={() => setShowCloseAll(false)}
      />
      <ConfirmDialog
        open={showCloseCalls}
        title="Close All Calls"
        message={`Close all ${summary.callCount} CALL position(s)?`}
        confirmLabel="Close Calls"
        variant="default"
        onConfirm={() => { setShowCloseCalls(false); closeCalls(); }}
        onCancel={() => setShowCloseCalls(false)}
      />
      <ConfirmDialog
        open={showClosePuts}
        title="Close All Puts"
        message={`Close all ${summary.putCount} PUT position(s)?`}
        confirmLabel="Close Puts"
        variant="default"
        onConfirm={() => { setShowClosePuts(false); closePuts(); }}
        onCancel={() => setShowClosePuts(false)}
      />
    </div>
  );
});

/** Sortable table header */
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

/** Mini stat card */
function MiniStat({
  icon: Icon,
  iconColor,
  label,
  value,
  valueColor,
}: {
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="rounded-md border border-border/25 bg-card p-2 card-elevated">
      <div className="flex items-center gap-1 mb-0.5">
        <Icon className={cn("h-2.5 w-2.5", iconColor)} />
        <span className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">{label}</span>
      </div>
      <p className={cn("text-sm font-bold font-mono tabular-nums", valueColor)}>{value}</p>
    </div>
  );
}
