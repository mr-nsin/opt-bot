import { memo, useEffect, useState, useRef } from "react";
import { Clock, Moon, Sun, Shield, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ModeToggle } from "@/components/common/ModeToggle";
import { useTradingStore } from "@/stores/tradingStore";
import { useTheme } from "@/hooks/useTheme";
import { useLicense } from "@/hooks/useLicense";
import { cn } from "@/lib/utils";

function HeaderInner() {
  const status = useTradingStore((s) => s.status);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const { isDark, toggleTheme } = useTheme();
  const { licenseStatus } = useLicense();
  const [clock, setClock] = useState("");
  const [date, setDate] = useState("");

  // PnL flash
  const prevPnlRef = useRef(dailyPnl.total);
  const [pnlFlash, setPnlFlash] = useState("");

  useEffect(() => {
    const prev = prevPnlRef.current;
    if (prev !== dailyPnl.total) {
      const cls = dailyPnl.total > prev ? "pnl-flash-profit" : dailyPnl.total < prev ? "pnl-flash-loss" : "";
      if (cls) {
        setPnlFlash(cls);
        const t = setTimeout(() => setPnlFlash(""), 600);
        prevPnlRef.current = dailyPnl.total;
        return () => clearTimeout(t);
      }
    }
    prevPnlRef.current = dailyPnl.total;
  }, [dailyPnl.total]);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          timeZone: "America/New_York",
        })
      );
      setDate(
        now.toLocaleDateString("en-US", {
          weekday: "short",
          month: "short",
          day: "numeric",
          timeZone: "America/New_York",
        })
      );
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const isRunning = status === "Running";
  const pnlValue = dailyPnl.total;
  const pnlColor =
    pnlValue > 0
      ? "text-emerald-500"
      : pnlValue < 0
        ? "text-red-500"
        : "text-muted-foreground";
  const pnlSign = pnlValue > 0 ? "+" : "";
  const PnlIcon = pnlValue > 0 ? TrendingUp : pnlValue < 0 ? TrendingDown : Minus;

  return (
    <header
      className={cn(
        "h-12 bg-card border-b flex items-center justify-between px-5 shrink-0 transition-all",
        !connectedToTws && isRunning && "tws-disconnected-border"
      )}
    >
      {/* Left: Trading status + key metrics */}
      <div className="flex items-center gap-4">
        {isRunning && (
          <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-500 rounded-md px-2.5 py-1 border border-emerald-500/20">
            <span className="h-2 w-2 rounded-full bg-emerald-500 live-dot" />
            <span className="text-xs font-bold tracking-wide">LIVE</span>
          </div>
        )}

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {licenseStatus?.valid && (
            <>
              <div className="flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5 text-emerald-500" />
                <span className={cn(
                  "font-mono font-semibold tabular-nums",
                  licenseStatus.days_remaining <= 7 ? "text-amber-500" : "text-emerald-500"
                )}>
                  {licenseStatus.days_remaining}d
                </span>
              </div>
              <div className="h-3 w-px bg-border/50" />
            </>
          )}

          {/* P&L with flash */}
          <div className="flex items-center gap-1.5">
            <PnlIcon className={cn("h-3 w-3", pnlColor)} />
            <span className="text-muted-foreground/50">P&L</span>
            <span
              className={cn(
                "font-mono font-bold tabular-nums rounded-sm px-1 transition-colors",
                pnlColor,
                pnlFlash
              )}
            >
              {pnlSign}${Math.abs(pnlValue).toFixed(2)}
            </span>
          </div>

          <div className="h-3 w-px bg-border/50" />

          {/* Realized / Unrealized mini */}
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground/40">R:</span>
            <span className={cn(
              "font-mono tabular-nums text-2xs",
              dailyPnl.realized > 0 ? "text-emerald-500/80" : dailyPnl.realized < 0 ? "text-red-500/80" : "text-muted-foreground/40"
            )}>
              ${Math.abs(dailyPnl.realized).toFixed(0)}
            </span>
            <span className="text-muted-foreground/40">U:</span>
            <span className={cn(
              "font-mono tabular-nums text-2xs",
              dailyPnl.unrealized > 0 ? "text-emerald-500/80" : dailyPnl.unrealized < 0 ? "text-red-500/80" : "text-muted-foreground/40"
            )}>
              ${Math.abs(dailyPnl.unrealized).toFixed(0)}
            </span>
          </div>

          <div className="h-3 w-px bg-border/50" />

          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground/50">Trades</span>
            <span className="font-mono font-semibold tabular-nums">{totalTrades}</span>
          </div>
        </div>
      </div>

      {/* Right: Clock, Mode, Theme */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5 text-muted-foreground/40" />
          <span className="font-mono tabular-nums">{clock}</span>
          <span className="text-muted-foreground/40">ET</span>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">{date}</span>
        </div>
        <div className="h-4 w-px bg-border/50" />
        <ModeToggle />
        <button
          onClick={toggleTheme}
          className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
          title="Toggle theme"
        >
          {isDark ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-500" />
          )}
        </button>
      </div>
    </header>
  );
}

export const Header = memo(HeaderInner);
