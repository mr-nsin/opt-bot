import { memo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  X,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronRight,
  Clock,
  Target,
  ShieldAlert,
  BarChart3,
} from "lucide-react";
import type { Position } from "@/lib/types";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { usePositions } from "@/hooks/usePositions";

export const PositionRow = memo(function PositionRow({ position }: { position: Position }) {
  const { closePosition } = usePositions();
  const [expanded, setExpanded] = useState(false);

  const pnl = position.pnl ?? 0;
  const pnlPct = position.pnl_percent ?? 0;
  const isProfit = pnl > 0;
  const gaugePct = Math.min(100, Math.abs(pnlPct));

  const entryTime = position.entry_time;
  const timeHeld = entryTime
    ? formatTimeHeld(new Date(entryTime as string), new Date())
    : null;

  return (
    <>
      <tr
        className={cn(
          "transition-colors group cursor-pointer",
          expanded && "!bg-muted/20"
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <td className="w-6">
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground/50" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground/20 group-hover:text-muted-foreground/50 transition-colors" />
          )}
        </td>

        <td>
          <div className="flex items-center gap-1">
            <span className="font-mono font-bold text-[11px]">{position.symbol}</span>
            {isProfit ? (
              <TrendingUp className="h-2.5 w-2.5 text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : pnl < 0 ? (
              <TrendingDown className="h-2.5 w-2.5 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : null}
          </div>
        </td>

        <td>
          <Badge variant={position.right === "C" ? "success" : "danger"} className="text-[9px] font-bold px-1.5 py-0">
            {position.right === "C" ? "CALL" : "PUT"}
          </Badge>
        </td>

        <td className="font-mono tabular-nums text-[11px]">${position.strike?.toFixed(1)}</td>
        <td className="text-muted-foreground/60 text-[10px]">{position.expiry}</td>
        <td className="font-mono tabular-nums text-[11px]">{position.quantity}</td>
        <td className="font-mono tabular-nums text-muted-foreground/70 text-[11px]">${position.avg_price?.toFixed(2)}</td>
        <td className="font-mono tabular-nums font-medium text-[11px]">${position.current_price?.toFixed(2)}</td>

        {/* P&L with gauge */}
        <td>
          <div className="space-y-0.5">
            <div className="flex items-center gap-1">
              <span className={cn("font-mono font-bold tabular-nums text-[11px]", pnlColor(pnl))}>
                {formatCurrency(pnl)}
              </span>
              <span className={cn("text-[9px] font-mono tabular-nums opacity-50", pnlColor(pnl))}>
                ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%)
              </span>
            </div>
            <div className="pnl-gauge w-14">
              <div
                className={cn("pnl-gauge-fill", isProfit ? "bg-emerald-500" : "bg-red-500")}
                style={{ width: `${gaugePct}%` }}
              />
            </div>
          </div>
        </td>

        <td>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              closePosition(position.symbol);
            }}
            className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-5 px-1 text-[9px] opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <X className="h-2.5 w-2.5 mr-0.5" /> Close
          </Button>
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={10} className="!p-0">
            <div className="px-3 py-2 bg-muted/10 border-t border-border/10">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px] animate-fade-up">
                <DetailItem icon={Target} label="Entry Price" value={`$${position.avg_price?.toFixed(2) ?? "—"}`} color="text-foreground" />
                <DetailItem icon={BarChart3} label="Current Bid" value={`$${position.current_price?.toFixed(2) ?? "—"}`} color="text-foreground" />
                {position.profit_price !== undefined && (
                  <DetailItem icon={TrendingUp} label="Take Profit" value={`$${Number(position.profit_price).toFixed(2)}`} color="text-emerald-400" />
                )}
                {position.stoploss_price !== undefined && (
                  <DetailItem icon={ShieldAlert} label="Stop Loss" value={`$${Number(position.stoploss_price).toFixed(2)}`} color="text-red-400" />
                )}
                {timeHeld && (
                  <DetailItem icon={Clock} label="Time Held" value={timeHeld} color="text-muted-foreground" />
                )}
                {position.quantity && position.current_price && (
                  <DetailItem icon={BarChart3} label="Market Value" value={formatCurrency(position.quantity * position.current_price * 100)} color="text-foreground" />
                )}
                {position.delta !== undefined && (
                  <DetailItem icon={BarChart3} label="Delta" value={Number(position.delta).toFixed(3)} color="text-blue-400" />
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
});

function DetailItem({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={cn("h-2.5 w-2.5 shrink-0", color, "opacity-40")} />
      <div>
        <p className="text-muted-foreground/50 text-[9px]">{label}</p>
        <p className={cn("font-mono font-semibold tabular-nums", color)}>{value}</p>
      </div>
    </div>
  );
}

function formatTimeHeld(from: Date, to: Date): string {
  const diffMs = to.getTime() - from.getTime();
  if (diffMs < 0) return "—";
  const mins = Math.floor(diffMs / 60000);
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hours > 0) return `${hours}h ${remainMins}m`;
  return `${mins}m`;
}
