import { useEffect, useState, useMemo, memo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PositionRow } from "./PositionRow";
import { PositionHistory } from "./PositionHistory";
import { usePositions } from "@/hooks/usePositions";
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
} from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import type { Position } from "@/lib/types";

type SortField = "symbol" | "pnl" | "strike" | "qty";
type SortDir = "asc" | "desc";

export const PositionsPage = memo(function PositionsPage() {
  const { positions, closedPositions, loading, refreshPositions, closeAll } = usePositions();
  const [showCloseAll, setShowCloseAll] = useState(false);
  const [sortField, setSortField] = useState<SortField>("pnl");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    refreshPositions();
    const i = setInterval(refreshPositions, 5000);
    return () => clearInterval(i);
  }, [refreshPositions]);

  // Toggle sort
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

  // Sort positions
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

  // Position summary stats
  const summary = useMemo(() => {
    const totalPnl = positions.reduce((s, p) => s + (p.pnl ?? 0), 0);
    const callCount = positions.filter((p) => p.right === "C").length;
    const putCount = positions.filter((p) => p.right === "P").length;
    return { totalPnl, callCount, putCount };
  }, [positions]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-2.5 w-2.5 text-muted-foreground/30" />;
    return sortDir === "asc" ? (
      <ArrowUp className="h-2.5 w-2.5 text-primary" />
    ) : (
      <ArrowDown className="h-2.5 w-2.5 text-primary" />
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold tracking-tight flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            Positions
          </h2>
          <p className="text-2xs text-muted-foreground">Active and closed positions</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refreshPositions} disabled={loading}>
            <RefreshCw className={`h-3 w-3 mr-1.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          {positions.length > 0 && (
            <Button variant="destructive" size="sm" onClick={() => setShowCloseAll(true)}>
              <XCircle className="h-3 w-3 mr-1.5" /> Close All
            </Button>
          )}
        </div>
      </div>

      {/* Position summary cards */}
      {positions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <SummaryCard
            icon={Target}
            iconColor="text-muted-foreground"
            label="Active"
            value={String(positions.length)}
          />
          <SummaryCard
            icon={summary.totalPnl >= 0 ? TrendingUp : TrendingDown}
            iconColor={summary.totalPnl >= 0 ? "text-emerald-500" : "text-red-500"}
            label="Total P&L"
            value={formatCurrency(summary.totalPnl)}
            valueColor={pnlColor(summary.totalPnl)}
          />
          <SummaryCard
            icon={TrendingUp}
            iconColor="text-emerald-500"
            label="Calls"
            value={String(summary.callCount)}
            valueColor="text-emerald-500"
          />
          <SummaryCard
            icon={TrendingDown}
            iconColor="text-red-500"
            label="Puts"
            value={String(summary.putCount)}
            valueColor="text-red-500"
          />
        </div>
      )}

      <Card>
        <CardHeader className="py-2 flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Briefcase className="h-3.5 w-3.5" />
            Active Positions
          </CardTitle>
          <Badge variant={positions.length > 0 ? "success" : "secondary"} className="text-2xs">
            {positions.length}
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {loading && positions.length === 0 ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full rounded-md" />
              ))}
            </div>
          ) : positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10">
              <Briefcase className="h-8 w-8 text-muted-foreground/15 mb-2" />
              <p className="text-center text-xs text-muted-foreground">No active positions</p>
              <p className="text-center text-2xs text-muted-foreground/40 mt-0.5">
                Positions will appear when trades are executed
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-muted-foreground text-left bg-muted/20">
                    <th className="py-1.5 pl-2 pr-1 w-6" />
                    <SortableHeader field="symbol" label="Symbol" sort={sortField} dir={sortDir} onClick={toggleSort} />
                    <th className="py-1.5 pr-3 font-semibold text-2xs uppercase tracking-wider">Type</th>
                    <SortableHeader field="strike" label="Strike" sort={sortField} dir={sortDir} onClick={toggleSort} />
                    <th className="py-1.5 pr-3 font-semibold text-2xs uppercase tracking-wider">Expiry</th>
                    <SortableHeader field="qty" label="Qty" sort={sortField} dir={sortDir} onClick={toggleSort} />
                    <th className="py-1.5 pr-3 font-semibold text-2xs uppercase tracking-wider">Avg</th>
                    <th className="py-1.5 pr-3 font-semibold text-2xs uppercase tracking-wider">Current</th>
                    <SortableHeader field="pnl" label="P&L" sort={sortField} dir={sortDir} onClick={toggleSort} />
                    <th className="py-1.5 font-semibold text-2xs uppercase tracking-wider" />
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
    </div>
  );
});

/** Sortable table header */
function SortableHeader({
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
        "py-1.5 pr-3 font-semibold text-2xs uppercase tracking-wider cursor-pointer select-none transition-colors",
        isActive ? "text-primary" : "hover:text-foreground/70"
      )}
      onClick={() => onClick(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {isActive ? (
          dir === "asc" ? (
            <ArrowUp className="h-2.5 w-2.5" />
          ) : (
            <ArrowDown className="h-2.5 w-2.5" />
          )
        ) : (
          <ArrowUpDown className="h-2.5 w-2.5 text-muted-foreground/30" />
        )}
      </div>
    </th>
  );
}

/** Summary card mini component */
function SummaryCard({
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
    <div className="rounded-lg border border-border/50 bg-card p-2.5">
      <div className="flex items-center gap-1.5 mb-0.5">
        <Icon className={cn("h-3 w-3", iconColor)} />
        <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
      </div>
      <p className={cn("text-lg font-bold tabular-nums", valueColor)}>{value}</p>
    </div>
  );
}
