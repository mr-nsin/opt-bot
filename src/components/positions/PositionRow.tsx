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
            <span className="font-mono font-bold text-xs">{position.symbol}</span>
            {isProfit ? (
              <TrendingUp className="h-2.5 w-2.5 text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : pnl < 0 ? (
              <TrendingDown className="h-2.5 w-2.5 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : null}
          </div>
        </td>

        <td className="text-center">
          <Badge variant={position.right === "C" || position.right === "CALL" ? "success" : "danger"} className="text-xs font-bold px-1.5 py-0">
            {position.right === "C" || position.right === "CALL" ? "CALL" : "PUT"}
          </Badge>
        </td>

        <td className="font-mono tabular-nums text-xs text-right">${position.strike?.toFixed(1)}</td>
        <td className="text-muted-foreground/70 text-xs">{position.expiry}</td>
        <td className="font-mono tabular-nums text-xs text-right">{position.quantity}</td>

        {/* Entry / Current — stacked like Bid/Ask */}
        <td className="text-xs font-mono tabular-nums text-right">
          <span className="flex flex-col gap-0.5 items-end">
            <span className="text-muted-foreground/80" title="Entry (avg cost)">
              ${position.avg_price?.toFixed(2)}
            </span>
            <span className="font-medium" title="Current market price">
              ${position.current_price?.toFixed(2)}
            </span>
          </span>
        </td>

        {/* Bid / Ask — visible in main row when available */}
        <td className="text-xs font-mono tabular-nums text-right">
          {(position.bid != null && position.bid > 0) || (position.ask != null && position.ask > 0) ? (
            <span className="flex flex-col gap-0.5 items-end">
              {position.bid != null && position.bid > 0 && <span>${Number(position.bid).toFixed(2)}</span>}
              {position.ask != null && position.ask > 0 && <span className="text-muted-foreground/80">${Number(position.ask).toFixed(2)}</span>}
            </span>
          ) : (
            <span className="text-muted-foreground/40">—</span>
          )}
        </td>

        {/* TP | SL — visible in main row when set */}
        <td className="text-xs text-right">
          {(position.profit_price != null && position.profit_price > 0) || (position.stoploss_price != null && position.stoploss_price > 0) ? (
            <span className="flex flex-col gap-0.5 items-end">
              {position.profit_price != null && position.profit_price > 0 && (
                <span className="text-emerald-500/90 font-mono tabular-nums" title="Take Profit">
                  TP ${Number(position.profit_price).toFixed(2)}{position.trailing_active ? " ↺" : ""}
                </span>
              )}
              {position.stoploss_price != null && position.stoploss_price > 0 && (
                <span className="text-red-500/90 font-mono tabular-nums" title="Stop Loss">
                  SL ${Number(position.stoploss_price).toFixed(2)}
                </span>
              )}
            </span>
          ) : (
            <span className="text-muted-foreground/40">—</span>
          )}
        </td>

        {/* P&L with gauge */}
        <td className="text-right">
          <div className="space-y-0.5 inline-block text-right">
            <div className="flex items-center gap-1 justify-end">
              <span className={cn("font-mono font-bold tabular-nums text-xs", pnlColor(pnl))}>
                {formatCurrency(pnl)}
              </span>
              <span className={cn("text-xs font-mono tabular-nums opacity-50", pnlColor(pnl))}>
                ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%)
              </span>
            </div>
            <div className="pnl-gauge w-14 ml-auto">
              <div
                className={cn("pnl-gauge-fill", isProfit ? "bg-emerald-500" : "bg-red-500")}
                style={{ width: `${gaugePct}%` }}
              />
            </div>
          </div>
        </td>

        <td className="text-right">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              closePosition(position.symbol, position.strike, position.right, position.expiry);
            }}
            className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-5 px-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <X className="h-2.5 w-2.5 mr-0.5" /> Close
          </Button>
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={13} className="!p-0">
            <div className="px-3 py-2 bg-muted/10 border-t border-border/10">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 text-xs animate-fade-up">
                <DetailItem icon={Target} label="Entry Price" value={`$${position.avg_price?.toFixed(2) ?? "—"}`} color="text-foreground" />
                <DetailItem icon={BarChart3} label="Current" value={`$${position.current_price?.toFixed(2) ?? "—"}`} color="text-foreground" />
                {(position.bid != null && position.bid > 0) && (
                  <DetailItem icon={BarChart3} label="Bid" value={`$${Number(position.bid).toFixed(2)}`} color="text-foreground" title="Used for TP/SL when available" />
                )}
                {(position.ask != null && position.ask > 0) && (
                  <DetailItem icon={BarChart3} label="Ask" value={`$${Number(position.ask).toFixed(2)}`} color="text-muted-foreground" title="For display only; not used in TP/SL" />
                )}
                {(position.last != null && position.last > 0) && (
                  <DetailItem icon={BarChart3} label="Last" value={`$${Number(position.last).toFixed(2)}`} color="text-foreground" />
                )}
                {(position.exit_price_used != null && position.exit_price_used > 0) && (
                  <DetailItem
                    icon={BarChart3}
                    label="Exit price used"
                    value={`$${Number(position.exit_price_used).toFixed(2)} (${position.exit_price_source ?? "—"})`}
                    color="text-amber-500/90"
                    title="TP/SL logic: bid when valid, else last. Ask not used."
                  />
                )}
                {position.profit_price !== undefined && position.profit_price > 0 && (
                  <DetailItem
                    icon={TrendingUp}
                    label={position.trailing_active ? "Take Profit (trailing)" : "Take Profit"}
                    value={`$${Number(position.profit_price).toFixed(2)}`}
                    color="text-emerald-400"
                  />
                )}
                {position.stoploss_price !== undefined && position.stoploss_price > 0 && (
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
              {(position.exit_price_used != null && position.exit_price_used > 0) && (
                <p className="mt-2 text-[10px] text-muted-foreground/60">
                  TP/SL logic: Exit price = <span className="font-mono">{position.exit_price_source}</span> when valid. Ask is not used for closing.
                </p>
              )}
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
  title,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
  title?: string;
}) {
  return (
    <div className="flex items-center gap-1.5" title={title}>
      <Icon className={cn("h-2.5 w-2.5 shrink-0", color, "opacity-40")} />
      <div>
        <p className="text-muted-foreground/50 text-xs">{label}</p>
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
