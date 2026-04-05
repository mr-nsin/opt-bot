import { RefreshCw, TrendingUp, TrendingDown, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * One surface only: the frosted `dock` is the background. Inner controls must not
 * add a second bordered pill (that caused “button inside a button” for Refresh).
 */
const dock = cn(
  "relative inline-flex flex-wrap items-center gap-0.5 rounded-[1.25rem] p-1",
  /* Light: warm glass on coffee-cream page */
  "border border-stone-400/45 bg-stone-900/[0.035]",
  "shadow-[0_6px_24px_-8px_rgba(55,45,35,0.12),inset_0_1px_0_0_rgba(255,255,255,0.65)]",
  "backdrop-blur-xl backdrop-saturate-150",
  "dark:border-white/10 dark:bg-white/[0.05] dark:shadow-[0_12px_40px_-12px_rgba(0,0,0,0.5),inset_0_1px_0_0_rgba(255,255,255,0.06)]"
);

const chip = cn(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap",
  "h-9 min-h-9 rounded-xl px-3.5 text-[13px] font-medium tracking-wide",
  "transition-all duration-200 ease-out",
  "disabled:pointer-events-none disabled:opacity-45",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
  "dark:focus-visible:ring-white/30",
  "active:scale-[0.98]"
);

/** Sits ON the dock — no extra box; hover is the only second state */
const chipNeutral = cn(
  chip,
  "border-0 bg-transparent text-foreground/95 shadow-none",
  "hover:bg-stone-900/[0.06] dark:text-white/90 dark:hover:bg-white/[0.08]"
);

/** Filled actions: gradient only, no second outline (dock already frames the group) */
const chipEmerald = cn(
  chip,
  "border-0 text-emerald-950",
  "bg-gradient-to-br from-emerald-300/70 via-emerald-500/45 to-emerald-800/50",
  "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.25)]",
  "hover:brightness-105",
  "dark:from-emerald-500/55 dark:via-emerald-600/40 dark:to-emerald-950/60 dark:text-emerald-50",
  "dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)] dark:hover:brightness-110"
);

const chipRose = cn(
  chip,
  "border-0 text-rose-950",
  "bg-gradient-to-br from-rose-300/70 via-rose-500/45 to-rose-900/50",
  "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.25)]",
  "hover:brightness-105",
  "dark:from-rose-500/55 dark:via-rose-600/40 dark:to-rose-950/60 dark:text-rose-50",
  "dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)] dark:hover:brightness-110"
);

const chipDanger = cn(
  chip,
  "border-0 text-white",
  "bg-gradient-to-br from-orange-500 via-rose-600 to-red-900",
  "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.2)]",
  "hover:brightness-110",
  "dark:from-orange-600 dark:via-red-700 dark:to-red-950"
);

type Props = {
  loading: boolean;
  hasPositions: boolean;
  callCount: number;
  putCount: number;
  onRefresh: () => void;
  onCloseCalls: () => void;
  onClosePuts: () => void;
  onCloseAll: () => void;
};

export function PositionActionToolbar({
  loading,
  hasPositions,
  callCount,
  putCount,
  onRefresh,
  onCloseCalls,
  onClosePuts,
  onCloseAll,
}: Props) {
  return (
    <div className="flex flex-wrap items-center justify-end">
      <div className={dock}>
        <button type="button" onClick={onRefresh} disabled={loading} className={chipNeutral}>
          <RefreshCw className={cn("h-4 w-4 shrink-0 opacity-90", loading && "animate-spin")} />
          <span>Refresh</span>
        </button>

        {hasPositions && (
          <>
            <button
              type="button"
              onClick={onCloseCalls}
              disabled={callCount === 0}
              title="Market-close all open CALL legs tracked by the bot"
              className={chipEmerald}
            >
              <TrendingUp className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Close Call</span>
            </button>
            <button
              type="button"
              onClick={onClosePuts}
              disabled={putCount === 0}
              title="Market-close all open PUT legs tracked by the bot"
              className={chipRose}
            >
              <TrendingDown className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Close Put</span>
            </button>
            <button type="button" onClick={onCloseAll} className={chipDanger}>
              <XCircle className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Close All</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
