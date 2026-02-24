import { useEffect, useState, useMemo, memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PositionRow } from "./PositionRow";
import { PositionHistory } from "./PositionHistory";
import { usePositions } from "@/hooks/usePositions";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, XCircle, Briefcase, TrendingUp, TrendingDown, Target } from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";

export const PositionsPage = memo(function PositionsPage() {
  const { positions, closedPositions, loading, refreshPositions, closeAll } = usePositions();
  const [showCloseAll, setShowCloseAll] = useState(false);

  useEffect(() => {
    refreshPositions();
    const i = setInterval(refreshPositions, 5000);
    return () => clearInterval(i);
  }, [refreshPositions]);

  // Position summary stats
  const summary = useMemo(() => {
    const totalPnl = positions.reduce((s, p) => s + (p.pnl ?? 0), 0);
    const callCount = positions.filter((p) => p.right === "C").length;
    const putCount = positions.filter((p) => p.right === "P").length;
    return { totalPnl, callCount, putCount };
  }, [positions]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-muted-foreground" />
            Positions
          </h2>
          <p className="text-xs text-muted-foreground">Active and closed positions</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refreshPositions} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          {positions.length > 0 && (
            <Button variant="destructive" size="sm" onClick={() => setShowCloseAll(true)}>
              <XCircle className="h-3.5 w-3.5 mr-1.5" /> Close All
            </Button>
          )}
        </div>
      </div>

      {/* Position summary cards */}
      {positions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-xl border border-border/70 bg-card p-3">
            <div className="flex items-center gap-2 mb-1">
              <Target className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">Active</span>
            </div>
            <p className="text-xl font-bold tabular-nums">{positions.length}</p>
          </div>
          <div className="rounded-xl border border-border/70 bg-card p-3">
            <div className="flex items-center gap-2 mb-1">
              {summary.totalPnl >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">Total P&L</span>
            </div>
            <p className={cn("text-xl font-bold tabular-nums", pnlColor(summary.totalPnl))}>
              {formatCurrency(summary.totalPnl)}
            </p>
          </div>
          <div className="rounded-xl border border-border/70 bg-card p-3">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">Calls</span>
            </div>
            <p className="text-xl font-bold tabular-nums text-emerald-500">{summary.callCount}</p>
          </div>
          <div className="rounded-xl border border-border/70 bg-card p-3">
            <div className="flex items-center gap-2 mb-1">
              <TrendingDown className="h-3.5 w-3.5 text-red-500" />
              <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">Puts</span>
            </div>
            <p className="text-xl font-bold tabular-nums text-red-500">{summary.putCount}</p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Briefcase className="h-3.5 w-3.5" />
            Active Positions
          </CardTitle>
          <Badge variant={positions.length > 0 ? "success" : "secondary"} className="text-2xs">
            {positions.length}
          </Badge>
        </CardHeader>
        <CardContent>
          {loading && positions.length === 0 ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full rounded-md" />
              ))}
            </div>
          ) : positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10">
              <Briefcase className="h-8 w-8 text-muted-foreground/20 mb-2" />
              <p className="text-center text-xs text-muted-foreground">No active positions</p>
              <p className="text-center text-2xs text-muted-foreground/50 mt-0.5">
                Positions will appear when trades are executed
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Symbol</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Type</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Strike</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Expiry</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Qty</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Avg</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">Current</th>
                    <th className="py-2 pr-3 font-semibold text-2xs uppercase tracking-wider">P&L</th>
                    <th className="py-2 font-semibold text-2xs uppercase tracking-wider"></th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
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
