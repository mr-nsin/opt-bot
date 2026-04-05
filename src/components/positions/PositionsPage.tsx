import { useEffect, useState, useMemo, memo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PositionRow } from "./PositionRow";
import { PositionHistory } from "./PositionHistory";
import { TradeBlotter } from "./TradeBlotter";
import { PositionActionToolbar } from "./PositionActionToolbar";
import { usePositions } from "@/hooks/usePositions";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Briefcase,
  TrendingUp,
  TrendingDown,
  Target,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Clock,
  Tag,
  Hash,
  BarChart3,
  DollarSign,
  Calendar,
  ShieldAlert,
  Settings2,
} from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import type { Position } from "@/lib/types";

type SortField = "time" | "symbol" | "pnl" | "strike" | "qty";
type SortDir = "asc" | "desc";

export const PositionsPage = memo(function PositionsPage() {
  const {
    positions,
    closedPositions,
    loading,
    refreshPositions,
    forceRefreshPositions,
    closeAll,
    closeCalls,
    closePuts,
  } = usePositions();
  const [showCloseAll, setShowCloseAll] = useState(false);
  const [showCloseCalls, setShowCloseCalls] = useState(false);
  const [showClosePuts, setShowClosePuts] = useState(false);
  const [sortField, setSortField] = useState<SortField>("time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    refreshPositions();
  }, [refreshPositions]);

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
        case "time": {
          const ta = a.entry_time ? new Date(a.entry_time as string).getTime() : 0;
          const tb = b.entry_time ? new Date(b.entry_time as string).getTime() : 0;
          cmp = ta - tb;
          break;
        }
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
        <PositionActionToolbar
          loading={loading}
          hasPositions={positions.length > 0}
          callCount={summary.callCount}
          putCount={summary.putCount}
          onRefresh={forceRefreshPositions}
          onCloseCalls={() => setShowCloseCalls(true)}
          onClosePuts={() => setShowClosePuts(true)}
          onCloseAll={() => setShowCloseAll(true)}
        />
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
          <div className="overflow-x-auto min-w-0">
            <table className="w-full table-pro min-w-max">
              <thead>
                <tr>
                  <th className="w-6" />
                  <SortTh field="time" label="Time" icon={Clock} sort={sortField} dir={sortDir} onClick={toggleSort} align="left" />
                  <SortTh field="symbol" label="Symbol" icon={Tag} sort={sortField} dir={sortDir} onClick={toggleSort} align="left" />
                  <th className="text-center">
                    <span className="flex items-center justify-center gap-1">
                      <Briefcase className="h-3 w-3 opacity-60" />
                      Type
                    </span>
                  </th>
                  <SortTh field="strike" label="Strike" icon={Target} sort={sortField} dir={sortDir} onClick={toggleSort} align="right" />
                  <th className="text-left">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 opacity-60" />
                      Expiry
                    </span>
                  </th>
                  <SortTh field="qty" label="Qty" icon={Hash} sort={sortField} dir={sortDir} onClick={toggleSort} align="right" />
                  <th className="text-right min-w-[5.5rem]" title="Average fill (entry) and live mark">
                    <span className="flex items-center justify-end gap-1">
                      <BarChart3 className="h-3 w-3 opacity-60" />
                      Entry / Current
                    </span>
                  </th>
                  <th className="text-right" title="Bid / Ask prices used for TP/SL">
                    <span className="flex items-center justify-end gap-1">
                      <BarChart3 className="h-3 w-3 opacity-60" />
                      Bid / Ask
                    </span>
                  </th>
                  <th className="text-left">
                    <span className="flex items-center gap-1">
                      <ShieldAlert className="h-3 w-3 opacity-60" />
                      TP / SL
                    </span>
                  </th>
                  <SortTh field="pnl" label="P&L" icon={DollarSign} sort={sortField} dir={sortDir} onClick={toggleSort} align="right" />
                  <th className="text-center w-16">
                    <span className="flex items-center justify-center gap-1">
                      <Settings2 className="h-3 w-3 opacity-60" />
                      Actions
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && positions.length === 0 ? (
                  <tr>
                    <td colSpan={12} className="p-3">
                      <div className="space-y-1">
                        {Array.from({ length: 3 }).map((_, i) => (
                          <Skeleton key={i} className="h-9 w-full rounded-md" />
                        ))}
                      </div>
                    </td>
                  </tr>
                ) : positions.length === 0 ? (
                  <tr>
                    <td colSpan={12}>
                      <div className="flex flex-col items-center justify-center py-8">
                        <Briefcase className="h-6 w-6 text-muted-foreground/10 mb-1.5" />
                        <p className="text-sm text-muted-foreground/70">No active positions</p>
                        <p className="text-xs text-muted-foreground/50 mt-0.5">
                          Positions appear when trades are executed
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  sortedPositions.map((p) => (
                    <PositionRow
                      key={`${p.symbol}-${p.strike}-${p.right}-${(p.expiry || "").replace(/-/g, "")}`}
                      position={p}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <TradeBlotter />

      <PositionHistory positions={closedPositions} />

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
        message={`Market-close all ${summary.callCount} open CALL position(s)? Puts are unchanged.`}
        confirmLabel="Close Calls"
        variant="destructive"
        onConfirm={() => { setShowCloseCalls(false); closeCalls(); }}
        onCancel={() => setShowCloseCalls(false)}
      />
      <ConfirmDialog
        open={showClosePuts}
        title="Close All Puts"
        message={`Market-close all ${summary.putCount} open PUT position(s)? Calls are unchanged.`}
        confirmLabel="Close Puts"
        variant="destructive"
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
  icon: Icon,
  align = "left",
}: {
  field: SortField;
  label: string;
  sort: SortField;
  dir: SortDir;
  onClick: (f: SortField) => void;
  icon?: React.ComponentType<{ className?: string }>;
  align?: "left" | "right";
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
