import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PositionRow } from "./PositionRow";
import { PositionHistory } from "./PositionHistory";
import { usePositions } from "@/hooks/usePositions";
import { RefreshCw, XCircle } from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";

export function PositionsPage() {
  const { positions, closedPositions, loading, refreshPositions, closeAll } = usePositions();
  const [showCloseAll, setShowCloseAll] = useState(false);

  useEffect(() => { refreshPositions(); const i = setInterval(refreshPositions, 5000); return () => clearInterval(i); }, [refreshPositions]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Positions</h2>
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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active</CardTitle>
          <Badge variant="secondary" className="text-2xs">{positions.length}</Badge>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <p className="text-center text-xs text-muted-foreground py-8">No active positions</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="py-2 pr-3 font-medium">Symbol</th>
                    <th className="py-2 pr-3 font-medium">Type</th>
                    <th className="py-2 pr-3 font-medium">Strike</th>
                    <th className="py-2 pr-3 font-medium">Expiry</th>
                    <th className="py-2 pr-3 font-medium">Qty</th>
                    <th className="py-2 pr-3 font-medium">Avg</th>
                    <th className="py-2 pr-3 font-medium">Current</th>
                    <th className="py-2 pr-3 font-medium">P&L</th>
                    <th className="py-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>{positions.map((p) => <PositionRow key={`${p.symbol}-${p.strike}-${p.right}`} position={p} />)}</tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <PositionHistory positions={closedPositions} />

      <ConfirmDialog open={showCloseAll} title="Close All Positions" message={`Close all ${positions.length} active position(s)?`} confirmLabel="Close All" variant="destructive" onConfirm={() => { setShowCloseAll(false); closeAll(); }} onCancel={() => setShowCloseAll(false)} />
    </div>
  );
}
