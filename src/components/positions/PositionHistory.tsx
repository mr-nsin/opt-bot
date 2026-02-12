import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Position } from "@/lib/types";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";

export function PositionHistory({ positions }: { positions: Position[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Closed</CardTitle>
        <Badge variant="secondary" className="text-2xs">{positions.length}</Badge>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <p className="text-center text-xs text-muted-foreground py-8">No closed positions today</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-muted-foreground text-left">
                  <th className="py-2 pr-3 font-medium">Symbol</th>
                  <th className="py-2 pr-3 font-medium">Type</th>
                  <th className="py-2 pr-3 font-medium">Strike</th>
                  <th className="py-2 pr-3 font-medium">Qty</th>
                  <th className="py-2 pr-3 font-medium">Entry</th>
                  <th className="py-2 pr-3 font-medium">Exit</th>
                  <th className="py-2 font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 pr-3 font-mono font-semibold">{p.symbol}</td>
                    <td className="py-2 pr-3"><Badge variant={p.right === "C" ? "success" : "danger"} className="text-2xs">{p.right === "C" ? "CALL" : "PUT"}</Badge></td>
                    <td className="py-2 pr-3 font-mono tabular-nums">${p.strike.toFixed(1)}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums">{p.quantity}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums">${p.avg_price.toFixed(2)}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums">${p.current_price.toFixed(2)}</td>
                    <td className={cn("py-2 font-mono font-semibold tabular-nums", pnlColor(p.pnl))}>{formatCurrency(p.pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
