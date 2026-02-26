import { memo, useEffect, useState, useRef } from "react";
import {
  Clock,
  Moon,
  Sun,
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  Wallet,
  Search,
  Activity,
} from "lucide-react";
import { ModeToggle } from "@/components/common/ModeToggle";
import { useTradingStore } from "@/stores/tradingStore";
import { useTheme } from "@/hooks/useTheme";
import { useLicense } from "@/hooks/useLicense";
import { cn, formatCurrency } from "@/lib/utils";
import { formatHotkey } from "@/hooks/useHotkeys";

function HeaderInner() {
  const status = useTradingStore((s) => s.status);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const accountMetrics = useTradingStore((s) => s.accountMetrics);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
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
      ? "text-emerald-400"
      : pnlValue < 0
        ? "text-red-400"
        : "text-muted-foreground";
  const pnlSign = pnlValue > 0 ? "+" : "";
  const PnlIcon = pnlValue > 0 ? TrendingUp : pnlValue < 0 ? TrendingDown : Minus;

  const netLiq = accountMetrics?.NetLiquidation;
  const buyingPower = accountMetrics?.BuyingPower;

  return (
    <header
      className={cn(
        "h-10 bg-card/85 backdrop-blur-md border-b border-border/25 flex items-center justify-between px-3 shrink-0 transition-all header-accent-line",
        !connectedToTws && isRunning && "tws-disconnected-border"
      )}
    >
      {/* Left: Trading status + Account + PnL */}
      <div className="flex items-center gap-2.5">
        {/* Status pill */}
        {isRunning ? (
          <div className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 rounded-md px-2 py-0.5 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 live-dot" />
            <span className="text-2xs font-bold tracking-wider">LIVE</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-muted-foreground/40 rounded-md px-2 py-0.5">
            <Activity className="h-3 w-3" />
            <span className="text-2xs font-medium">IDLE</span>
          </div>
        )}

        {/* Vertical separator */}
        <div className="h-4 w-px bg-border/20" />

        {/* Account balance bar (Trabot-style) */}
        {netLiq !== undefined && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-xs">
              <Wallet className="h-3 w-3 text-primary/50" />
              <span className="text-muted-foreground/40 text-2xs font-medium">NLV</span>
              <span className="font-mono font-bold tabular-nums text-foreground/90 text-xs">
                {formatCurrency(netLiq)}
              </span>
            </div>
            {buyingPower !== undefined && (
              <div className="flex items-center gap-1 text-2xs">
                <span className="text-muted-foreground/30 font-medium">BP</span>
                <span className="font-mono tabular-nums text-foreground/50">
                  {formatCurrency(buyingPower)}
                </span>
              </div>
            )}
          </div>
        )}

        <div className="h-4 w-px bg-border/20" />

        {/* P&L block — most critical data */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs">
            <PnlIcon className={cn("h-3.5 w-3.5", pnlColor)} />
            <span
              className={cn(
                "font-mono font-bold tabular-nums rounded px-1 py-0.5 transition-colors text-sm",
                pnlColor,
                pnlFlash
              )}
            >
              {pnlSign}${Math.abs(pnlValue).toFixed(2)}
            </span>
          </div>

          {/* Realized / Unrealized mini */}
          <div className="flex items-center gap-2 text-2xs">
            <span className="flex items-center gap-0.5">
              <span className="text-muted-foreground/25">R</span>
              <span className={cn(
                "font-mono tabular-nums",
                dailyPnl.realized > 0 ? "text-emerald-400/60" : dailyPnl.realized < 0 ? "text-red-400/60" : "text-muted-foreground/25"
              )}>
                ${Math.abs(dailyPnl.realized).toFixed(0)}
              </span>
            </span>
            <span className="flex items-center gap-0.5">
              <span className="text-muted-foreground/25">U</span>
              <span className={cn(
                "font-mono tabular-nums",
                dailyPnl.unrealized > 0 ? "text-emerald-400/60" : dailyPnl.unrealized < 0 ? "text-red-400/60" : "text-muted-foreground/25"
              )}>
                ${Math.abs(dailyPnl.unrealized).toFixed(0)}
              </span>
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-border/20" />

        {/* Trade stats */}
        <div className="flex items-center gap-1.5 text-2xs">
          <span className="text-muted-foreground/40 font-medium">Trades</span>
          <span className="font-mono font-bold tabular-nums text-foreground/80">{totalTrades}</span>
          {totalTrades > 0 && (
            <span className="text-muted-foreground/30">
              (<span className="text-emerald-400/60">{winningTrades}W</span>
              <span className="mx-0.5">/</span>
              <span className="text-red-400/60">{losingTrades}L</span>)
            </span>
          )}
        </div>
      </div>

      {/* Right: Search, Clock, License, Theme */}
      <div className="flex items-center gap-1.5">
        {/* Command palette trigger */}
        <button
          onClick={() => window.dispatchEvent(new CustomEvent("quantdrift:command-palette"))}
          className="flex items-center gap-1.5 h-6 px-2 rounded-md bg-muted/40 hover:bg-muted/60 text-muted-foreground/50 hover:text-muted-foreground transition-colors text-2xs border border-border/20"
        >
          <Search className="h-2.5 w-2.5" />
          <span className="hidden md:inline">Search</span>
          <kbd className="hidden md:flex items-center gap-0.5 px-1 rounded bg-background/40 font-mono text-2xs text-muted-foreground/30">
            {formatHotkey("K")}
          </kbd>
        </button>

        <div className="h-4 w-px bg-border/20" />

        {/* License */}
        {licenseStatus?.valid && (
          <div className="flex items-center gap-1 text-2xs">
            <Shield className="h-2.5 w-2.5 text-emerald-400/60" />
            <span className={cn(
              "font-mono font-semibold tabular-nums",
              (licenseStatus.days_remaining ?? 0) <= 7 ? "text-amber-400" : "text-emerald-400/60"
            )}>
              {licenseStatus.days_remaining}d
            </span>
          </div>
        )}

        {/* Clock */}
        <div className="flex items-center gap-1 text-2xs text-muted-foreground/40">
          <Clock className="h-2.5 w-2.5 text-muted-foreground/25" />
          <span className="font-mono tabular-nums text-foreground/50">{clock}</span>
          <span className="text-muted-foreground/20">{date}</span>
        </div>

        <div className="h-4 w-px bg-border/20" />

        <ModeToggle />
        <button
          onClick={toggleTheme}
          className="h-6 w-6 flex items-center justify-center rounded-md hover:bg-muted/40 transition-colors"
          title="Toggle theme"
        >
          {isDark ? (
            <Sun className="h-3 w-3 text-amber-400/70" />
          ) : (
            <Moon className="h-3 w-3 text-slate-500" />
          )}
        </button>
      </div>
    </header>
  );
}

export const Header = memo(HeaderInner);
