import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tag, Briefcase, Target, Hash, BarChart3, DollarSign, Clock } from "lucide-react";
import type { Position } from "@/lib/types";
import { cn, formatCurrency, formatTime, pnlColor } from "@/lib/utils";

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
          <div className="overflow-x-auto min-w-0">
            <table className="w-full table-pro text-xs min-w-max">
              <thead>
                <tr>
                  <th className="py-2 pr-3 font-medium text-left">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 opacity-60" />
                      Time
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-left">
                    <span className="flex items-center gap-1">
                      <Tag className="h-3 w-3 opacity-60" />
                      Symbol
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-center">
                    <span className="flex items-center justify-center gap-1">
                      <Briefcase className="h-3 w-3 opacity-60" />
                      Type
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Target className="h-3 w-3 opacity-60" />
                      Strike
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Hash className="h-3 w-3 opacity-60" />
                      Qty
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">
                    <span className="flex items-center justify-end gap-1">
                      <BarChart3 className="h-3 w-3 opacity-60" />
                      Entry
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">
                    <span className="flex items-center justify-end gap-1">
                      <BarChart3 className="h-3 w-3 opacity-60" />
                      Exit
                    </span>
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">
                    <span className="flex items-center justify-end gap-1">
                      <DollarSign className="h-3 w-3 opacity-60" />
                      P&L
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 pr-3 text-muted-foreground font-mono tabular-nums text-xs">{p.timestamp ? formatTime(p.timestamp as string) : "—"}</td>
                    <td className="py-2 pr-3 font-mono font-semibold text-xs">{p.symbol}</td>
                    <td className="py-2 pr-3 text-center"><Badge variant={p.right === "C" || p.right === "CALL" ? "success" : "danger"} className="text-2xs">{p.right === "C" || p.right === "CALL" ? "CALL" : "PUT"}</Badge></td>
                    <td className="py-2 pr-3 font-mono tabular-nums text-xs text-right">${p.strike?.toFixed(1) ?? "—"}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums text-xs text-right">{p.quantity}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums text-xs text-right">${(p.avg_price ?? p.entry_price ?? 0).toFixed(2)}</td>
                    <td className="py-2 pr-3 font-mono tabular-nums text-xs text-right">${(p.exit_price ?? p.current_price ?? 0).toFixed(2)}</td>
                    <td className={cn("py-2 pr-3 font-mono font-semibold tabular-nums text-xs text-right", pnlColor(p.pnl ?? 0))}>{formatCurrency(p.pnl ?? 0)}</td>
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
