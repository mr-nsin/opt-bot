import { memo, useEffect, useState, useRef } from "react";
import { Moon, Sun, Bell, Search, Activity, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useLogStore } from "@/stores/logStore";
import { ModeToggle } from "@/components/common/ModeToggle";
import { useTradingStore } from "@/stores/tradingStore";
import { useTheme } from "@/hooks/useTheme";
import { useNavigate } from "react-router-dom";
import { cn, formatCurrency } from "@/lib/utils";

function HeaderInner() {
  const status = useTradingStore((s) => s.status);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const accountMetrics = useTradingStore((s) => s.accountMetrics);
  const { isDark, toggleTheme } = useTheme();
  const prevPnlRef = useRef(dailyPnl.total);
  const [pnlFlash, setPnlFlash] = useState("");
  const logs = useLogStore((s) => s.logs);
  const notificationCount = logs.filter((l) => l.level === "ERROR").length;
  const navigate = useNavigate();

  useEffect(() => {
    const prev = prevPnlRef.current;
    if (prev !== dailyPnl.total) {
      const cls = dailyPnl.total > prev ? "pnl-flash-profit" : dailyPnl.total < prev ? "pnl-flash-loss" : "";
      if (cls) {
        setPnlFlash(cls);
        const t = setTimeout(() => setPnlFlash(""), 500);
        prevPnlRef.current = dailyPnl.total;
        return () => clearTimeout(t);
      }
    }
    prevPnlRef.current = dailyPnl.total;
  }, [dailyPnl.total]);

  const isRunning = status === "Running";
  const pnlValue = dailyPnl.total;
  const pnlColor =
    pnlValue > 0 ? "text-emerald-400" : pnlValue < 0 ? "text-red-400" : "text-muted-foreground";
  const pnlSign = pnlValue > 0 ? "+" : "";
  const PnlIcon = pnlValue > 0 ? TrendingUp : pnlValue < 0 ? TrendingDown : Minus;
  const netLiq = accountMetrics?.NetLiquidation;

  return (
    <header
      className={cn(
        "h-11 shrink-0 flex items-center justify-between px-4 border-b border-border/10",
        "bg-background/80 backdrop-blur-md",
        !connectedToTws && isRunning && "border-amber-500/30"
      )}
    >
      {/* Left: Status · Balance · Daily P&L only */}
      <div className="flex items-center gap-6">
        {isRunning ? (
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 live-dot" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Live</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-muted-foreground/50">
            <Activity className="h-3.5 w-3.5" />
            <span className="text-[11px] font-medium uppercase tracking-wider">Idle</span>
          </div>
        )}

        {netLiq !== undefined && (
          <span className="font-mono text-sm tabular-nums text-foreground/90" title="Net liquidation">
            {formatCurrency(netLiq)}
          </span>
        )}

        <div className="flex items-center gap-1.5">
          <PnlIcon className={cn("h-3.5 w-3.5 shrink-0", pnlColor)} />
          <span
            className={cn(
              "font-mono text-sm font-semibold tabular-nums transition-colors",
              pnlColor,
              pnlFlash
            )}
          >
            {pnlSign}${Math.abs(pnlValue).toFixed(2)}
          </span>
          <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Today</span>
        </div>
      </div>

      {/* Right: Logs · Search · Mode · Theme — icon-only, minimal */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={() => navigate("/logs")}
          className="relative h-8 w-8 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Logs"
        >
          <Bell className="h-4 w-4" />
          {notificationCount > 0 && (
            <span className="absolute top-0.5 right-0.5 min-w-[14px] h-3.5 flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold">
              {notificationCount > 99 ? "99+" : notificationCount}
            </span>
          )}
        </button>
        <button
          onClick={() => window.dispatchEvent(new CustomEvent("quantdrift:command-palette"))}
          className="h-8 w-8 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Search (⌘K)"
        >
          <Search className="h-4 w-4" />
        </button>
        <div className="w-px h-4 bg-border/20 mx-1" />
        <ModeToggle />
        <button
          onClick={toggleTheme}
          className="h-8 w-8 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Theme"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}

export const Header = memo(HeaderInner);
