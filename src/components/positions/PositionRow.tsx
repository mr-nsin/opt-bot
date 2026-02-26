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

  // Calculate gauge fill percentage (capped at 100% for visual)
  const gaugePct = Math.min(100, Math.abs(pnlPct));

  // Time held calculation
  const entryTime = position.entry_time;
  const timeHeld = entryTime
    ? formatTimeHeld(new Date(entryTime as string), new Date())
    : null;

  return (
    <>
      <tr
        className={cn(
          "border-b last:border-0 transition-colors group cursor-pointer",
          expanded ? "bg-muted/30" : "hover:bg-muted/30"
        )}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand chevron */}
        <td className="py-2 pl-2 pr-1 w-6">
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground/50" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground/30 group-hover:text-muted-foreground/50 transition-colors" />
          )}
        </td>

        {/* Symbol */}
        <td className="py-2 pr-3">
          <div className="flex items-center gap-1.5">
            <span className="font-mono font-bold text-xs">{position.symbol}</span>
            {isProfit ? (
              <TrendingUp className="h-3 w-3 text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : pnl < 0 ? (
              <TrendingDown className="h-3 w-3 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : null}
          </div>
        </td>

        {/* Type (CALL/PUT) */}
        <td className="py-2 pr-3">
          <Badge variant={position.right === "C" ? "success" : "danger"} className="text-2xs font-bold">
            {position.right === "C" ? "CALL" : "PUT"}
          </Badge>
        </td>

        {/* Strike */}
        <td className="py-2 pr-3 font-mono tabular-nums text-xs">${position.strike?.toFixed(1)}</td>

        {/* Expiry */}
        <td className="py-2 pr-3 text-muted-foreground text-2xs">{position.expiry}</td>

        {/* Qty */}
        <td className="py-2 pr-3 font-mono tabular-nums text-xs">{position.quantity}</td>

        {/* Avg Price */}
        <td className="py-2 pr-3 font-mono tabular-nums text-muted-foreground text-xs">${position.avg_price?.toFixed(2)}</td>

        {/* Current Price */}
        <td className="py-2 pr-3 font-mono tabular-nums font-medium text-xs">${position.current_price?.toFixed(2)}</td>

        {/* P&L with gauge */}
        <td className="py-2 pr-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5">
              <span className={cn("font-mono font-bold tabular-nums text-xs", pnlColor(pnl))}>
                {formatCurrency(pnl)}
              </span>
              <span className={cn("text-2xs font-mono tabular-nums opacity-60", pnlColor(pnl))}>
                ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%)
              </span>
            </div>
            <div className="pnl-gauge w-16">
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
        <td className="py-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              closePosition(position.symbol);
            }}
            className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-6 px-1.5 text-2xs opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <X className="h-3 w-3 mr-0.5" /> Close
          </Button>
        </td>
      </tr>

      {/* Expanded detail row */}
      {expanded && (
        <tr className="border-b last:border-0">
          <td colSpan={10} className="px-3 py-2 bg-muted/15">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-2xs animate-fade-up">
              {/* Entry details */}
              <DetailItem
                icon={Target}
                label="Entry Price"
                value={`$${position.avg_price?.toFixed(2) ?? "—"}`}
                color="text-foreground"
              />
              <DetailItem
                icon={BarChart3}
                label="Current Bid"
                value={`$${position.current_price?.toFixed(2) ?? "—"}`}
                color="text-foreground"
              />

              {/* TP / SL */}
              {position.profit_price !== undefined && (
                <DetailItem
                  icon={TrendingUp}
                  label="Take Profit"
                  value={`$${Number(position.profit_price).toFixed(2)}`}
                  color="text-emerald-500"
                />
              )}
              {position.stoploss_price !== undefined && (
                <DetailItem
                  icon={ShieldAlert}
                  label="Stop Loss"
                  value={`$${Number(position.stoploss_price).toFixed(2)}`}
                  color="text-red-500"
                />
              )}

              {/* Time held */}
              {timeHeld && (
                <DetailItem
                  icon={Clock}
                  label="Time Held"
                  value={timeHeld}
                  color="text-muted-foreground"
                />
              )}

              {/* Contract value */}
              {position.quantity && position.current_price && (
                <DetailItem
                  icon={BarChart3}
                  label="Market Value"
                  value={formatCurrency(position.quantity * position.current_price * 100)}
                  color="text-foreground"
                />
              )}

              {/* Delta / Greeks if available */}
              {position.delta !== undefined && (
                <DetailItem
                  icon={BarChart3}
                  label="Delta"
                  value={Number(position.delta).toFixed(3)}
                  color="text-blue-400"
                />
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
});

/** Helper: Detail row item */
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
    <div className="flex items-center gap-2">
      <Icon className={cn("h-3 w-3 shrink-0", color, "opacity-50")} />
      <div>
        <p className="text-muted-foreground/60">{label}</p>
        <p className={cn("font-mono font-semibold tabular-nums", color)}>{value}</p>
      </div>
    </div>
  );
}

/** Calculate human-readable time held */
function formatTimeHeld(from: Date, to: Date): string {
  const diffMs = to.getTime() - from.getTime();
  if (diffMs < 0) return "—";
  const mins = Math.floor(diffMs / 60000);
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hours > 0) return `${hours}h ${remainMins}m`;
  return `${mins}m`;
}
