import { memo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X, TrendingUp, TrendingDown } from "lucide-react";
import type { Position } from "@/lib/types";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { usePositions } from "@/hooks/usePositions";

export const PositionRow = memo(function PositionRow({ position }: { position: Position }) {
  const { closePosition } = usePositions();

  const pnl = position.pnl ?? 0;
  const pnlPct = position.pnl_percent ?? 0;
  const isProfit = pnl > 0;

  // Calculate gauge fill percentage (capped at 100% for visual)
  const gaugePct = Math.min(100, Math.abs(pnlPct));

  return (
    <tr className="border-b last:border-0 hover:bg-muted/50 transition-colors group">
      {/* Symbol */}
      <td className="py-2.5 pr-3">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sm">{position.symbol}</span>
          {isProfit ? (
            <TrendingUp className="h-3 w-3 text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          ) : pnl < 0 ? (
            <TrendingDown className="h-3 w-3 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          ) : null}
        </div>
      </td>

      {/* Type (CALL/PUT) */}
      <td className="py-2.5 pr-3">
        <Badge variant={position.right === "C" ? "success" : "danger"} className="text-2xs font-bold">
          {position.right === "C" ? "CALL" : "PUT"}
        </Badge>
      </td>

      {/* Strike */}
      <td className="py-2.5 pr-3 font-mono tabular-nums">${position.strike?.toFixed(1)}</td>

      {/* Expiry */}
      <td className="py-2.5 pr-3 text-muted-foreground text-2xs">{position.expiry}</td>

      {/* Qty */}
      <td className="py-2.5 pr-3 font-mono tabular-nums">{position.quantity}</td>

      {/* Avg Price */}
      <td className="py-2.5 pr-3 font-mono tabular-nums text-muted-foreground">${position.avg_price?.toFixed(2)}</td>

      {/* Current Price */}
      <td className="py-2.5 pr-3 font-mono tabular-nums font-medium">${position.current_price?.toFixed(2)}</td>

      {/* P&L with gauge */}
      <td className="py-2.5 pr-3">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <span className={cn("font-mono font-bold tabular-nums", pnlColor(pnl))}>
              {formatCurrency(pnl)}
            </span>
            <span className={cn("text-2xs font-mono tabular-nums opacity-60", pnlColor(pnl))}>
              ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%)
            </span>
          </div>
          {/* P&L gauge bar */}
          <div className="pnl-gauge w-20">
            <div
              className={cn(
                "pnl-gauge-fill",
                isProfit ? "bg-emerald-500" : "bg-red-500"
              )}
              style={{ width: `${gaugePct}%` }}
            />
          </div>
        </div>
      </td>

      {/* Close button */}
      <td className="py-2.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => closePosition(position.symbol)}
          className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-7 px-2 text-2xs opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X className="h-3 w-3 mr-0.5" /> Close
        </Button>
      </td>
    </tr>
  );
});
