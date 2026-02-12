import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import type { Position } from "@/lib/types";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { usePositions } from "@/hooks/usePositions";

export function PositionRow({ position }: { position: Position }) {
  const { closePosition } = usePositions();
  return (
    <tr className="border-b last:border-0 hover:bg-muted/50 transition-colors">
      <td className="py-2.5 pr-3 font-mono font-semibold">{position.symbol}</td>
      <td className="py-2.5 pr-3">
        <Badge variant={position.right === "C" ? "success" : "danger"} className="text-2xs">
          {position.right === "C" ? "CALL" : "PUT"}
        </Badge>
      </td>
      <td className="py-2.5 pr-3 font-mono tabular-nums">${position.strike.toFixed(1)}</td>
      <td className="py-2.5 pr-3 text-muted-foreground">{position.expiry}</td>
      <td className="py-2.5 pr-3 font-mono tabular-nums">{position.quantity}</td>
      <td className="py-2.5 pr-3 font-mono tabular-nums">${position.avg_price.toFixed(2)}</td>
      <td className="py-2.5 pr-3 font-mono tabular-nums">${position.current_price.toFixed(2)}</td>
      <td className={cn("py-2.5 pr-3 font-mono font-semibold tabular-nums", pnlColor(position.pnl))}>
        {formatCurrency(position.pnl)}
        <span className="text-2xs ml-1 text-muted-foreground font-normal">
          ({position.pnl_percent >= 0 ? "+" : ""}{position.pnl_percent.toFixed(1)}%)
        </span>
      </td>
      <td className="py-2.5">
        <Button variant="ghost" size="sm" onClick={() => closePosition(position.symbol)} className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-7 px-2 text-2xs">
          <X className="h-3 w-3 mr-0.5" /> Close
        </Button>
      </td>
    </tr>
  );
}
