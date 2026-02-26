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

  // Account balance from IBKR
  const netLiq = accountMetrics?.NetLiquidation;
  const buyingPower = accountMetrics?.BuyingPower;

  return (
    <header
      className={cn(
        "h-11 bg-card border-b border-border/50 flex items-center justify-between px-4 shrink-0 transition-all",
        !connectedToTws && isRunning && "tws-disconnected-border"
      )}
    >
      {/* Left: Trading status + Account + PnL */}
      <div className="flex items-center gap-3">
        {isRunning && (
          <div className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-500 rounded-md px-2 py-0.5 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 live-dot" />
            <span className="text-2xs font-bold tracking-wider">LIVE</span>
          </div>
        )}

        {/* Account balance (NinjaTrader-style) */}
        {netLiq !== undefined && (
          <>
            <div className="h-4 w-px bg-border/30" />
            <div className="flex items-center gap-1.5 text-xs">
              <Wallet className="h-3 w-3 text-primary/60" />
              <span className="text-muted-foreground/50 text-2xs">NLV</span>
              <span className="font-mono font-bold tabular-nums text-foreground/80">
                {formatCurrency(netLiq)}
              </span>
            </div>
          </>
        )}

        {buyingPower !== undefined && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground/40 text-2xs">BP</span>
            <span className="font-mono tabular-nums text-foreground/60 text-2xs">
              {formatCurrency(buyingPower)}
            </span>
          </div>
        )}

        <div className="h-4 w-px bg-border/30" />

        {/* P&L with flash */}
        <div className="flex items-center gap-1.5 text-xs">
          <PnlIcon className={cn("h-3 w-3", pnlColor)} />
          <span className="text-muted-foreground/40 text-2xs">P&L</span>
          <span
            className={cn(
              "font-mono font-bold tabular-nums rounded-sm px-0.5 transition-colors text-xs",
              pnlColor,
              pnlFlash
            )}
          >
            {pnlSign}${Math.abs(pnlValue).toFixed(2)}
          </span>
        </div>

        {/* Realized / Unrealized */}
        <div className="flex items-center gap-1.5 text-2xs">
          <span className="text-muted-foreground/30">R:</span>
          <span className={cn(
            "font-mono tabular-nums",
            dailyPnl.realized > 0 ? "text-emerald-500/70" : dailyPnl.realized < 0 ? "text-red-500/70" : "text-muted-foreground/30"
          )}>
            ${Math.abs(dailyPnl.realized).toFixed(0)}
          </span>
          <span className="text-muted-foreground/30">U:</span>
          <span className={cn(
            "font-mono tabular-nums",
            dailyPnl.unrealized > 0 ? "text-emerald-500/70" : dailyPnl.unrealized < 0 ? "text-red-500/70" : "text-muted-foreground/30"
          )}>
            ${Math.abs(dailyPnl.unrealized).toFixed(0)}
          </span>
        </div>

        <div className="h-4 w-px bg-border/30" />

        <div className="flex items-center gap-1 text-2xs text-muted-foreground/50">
          <span>Trades</span>
          <span className="font-mono font-semibold tabular-nums text-foreground/70">{totalTrades}</span>
        </div>
      </div>

      {/* Right: Search, Clock, License, Theme */}
      <div className="flex items-center gap-2">
        {/* Command palette trigger */}
        <button
          onClick={() => window.dispatchEvent(new CustomEvent("quantdrift:command-palette"))}
          className="flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-muted/50 hover:bg-muted text-muted-foreground/60 hover:text-muted-foreground transition-colors text-2xs"
        >
          <Search className="h-3 w-3" />
          <span className="hidden md:inline">Search…</span>
          <kbd className="hidden md:flex items-center gap-0.5 px-1 py-0.5 rounded bg-background/60 font-mono text-2xs text-muted-foreground/40">
            {formatHotkey("K")}
          </kbd>
        </button>

        <div className="h-4 w-px bg-border/30" />

        {/* License */}
        {licenseStatus?.valid && (
          <div className="flex items-center gap-1 text-2xs">
            <Shield className="h-3 w-3 text-emerald-500/70" />
            <span className={cn(
              "font-mono font-semibold tabular-nums",
              (licenseStatus.days_remaining ?? 0) <= 7 ? "text-amber-500" : "text-emerald-500/70"
            )}>
              {licenseStatus.days_remaining}d
            </span>
          </div>
        )}

        {/* Clock */}
        <div className="flex items-center gap-1.5 text-2xs text-muted-foreground/50">
          <Clock className="h-3 w-3 text-muted-foreground/30" />
          <span className="font-mono tabular-nums">{clock}</span>
          <span className="text-muted-foreground/30">{date}</span>
        </div>

        <div className="h-4 w-px bg-border/30" />

        <ModeToggle />
        <button
          onClick={toggleTheme}
          className="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent transition-colors"
          title="Toggle theme"
        >
          {isDark ? (
            <Sun className="h-3.5 w-3.5 text-amber-400" />
          ) : (
            <Moon className="h-3.5 w-3.5 text-slate-500" />
          )}
        </button>
      </div>
    </header>
  );
}

export const Header = memo(HeaderInner);
