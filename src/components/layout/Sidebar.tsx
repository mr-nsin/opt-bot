import { memo, useMemo } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  FileText,
  Settings,
  Activity,
  Shield,
  Wifi,
  WifiOff,
  AlertCircle,
  Zap,
  User,
  ChevronRight,
} from "lucide-react";
import { cn, pnlColor } from "@/lib/utils";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";

const LOGO_DARK = "/logo/bwquantDrift.png";
const LOGO_LIGHT = "/logo/quantDriftw.png";
import { useLogStore } from "@/stores/logStore";
import { useLicense } from "@/hooks/useLicense";
import { formatHotkey } from "@/hooks/useHotkeys";

const navGroups = [
  {
    label: "Trading",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, path: "/", hotkey: "1" },
      { id: "positions", label: "Positions", icon: Briefcase, path: "/positions", hotkey: "3" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { id: "analytics", label: "Analytics", icon: BarChart3, path: "/analytics", hotkey: "2" },
      { id: "logs", label: "Logs", icon: FileText, path: "/logs", hotkey: "4" },
    ],
  },
  {
    label: "System",
    items: [
      { id: "settings", label: "Settings", icon: Settings, path: "/settings", hotkey: "5" },
    ],
  },
];

function SidebarInner() {
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const status = useTradingStore((s) => s.status);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);
  const settings = useConfigStore((s) => s.settings);
  const logs = useLogStore((s) => s.logs);
  const { licenseStatus } = useLicense();
  const isRunning = status === "Running";
  const isDark = settings.theme === "dark";
  const isLive = settings.trading_mode === "live";
  const daysLeft = licenseStatus?.valid ? licenseStatus.days_remaining : null;

  const errorCount = useMemo(
    () => logs.filter((l) => l.level === "ERROR").length,
    [logs]
  );

  const winRate = closedTrades > 0 ? ((winningTrades / closedTrades) * 100).toFixed(0) : "—";

  return (
    <aside className="w-[260px] sidebar-pro flex flex-col border-r border-sidebar-border/20 shrink-0">
      {/* Brand */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-sidebar-border/15">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-primary via-primary/85 to-cyan-500/70 flex items-center justify-center shadow-lg shadow-primary/25">
          <Activity className="h-4 w-4 text-white" />
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-base font-bold text-sidebar-foreground tracking-tight leading-none">
            QuantDrift
          </span>
          <span className="text-[11px] text-sidebar-foreground/60 font-medium leading-none">
            Trading Terminal
          </span>
        </div>
      </div>

      {/* Logo — bwquantDrift for dark theme, quantDriftw for light */}
      <div className="flex justify-center items-center border-b border-sidebar-border/15 overflow-hidden h-[120px] mt-1">
        <img
          src={isDark ? LOGO_DARK : LOGO_LIGHT}
          alt="QuantDrift"
          className="w-full h-auto object-contain scale-[1.1] translate-y-2"
        />
      </div>

      {/* Navigation groups — TRADING, ANALYSIS, SYSTEM below logo */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="text-sm font-bold uppercase tracking-wider text-sidebar-foreground/80 px-3 mb-2">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const showBadge = item.id === "logs" && errorCount > 0;
                const showSignalBadge = item.id === "dashboard" && isSignalScanning && isRunning;

                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-base font-semibold transition-all group relative",
                        isActive
                          ? "sidebar-active-glow text-primary"
                          : "text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-muted/40"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary shadow-sm shadow-primary/30" />
                        )}
                        <Icon
                          className={cn(
                            "h-5 w-5 shrink-0 transition-colors",
                            isActive
                              ? "text-primary"
                              : "text-sidebar-foreground/60 group-hover:text-sidebar-foreground/90"
                          )}
                        />
                        <span className="flex-1">{item.label}</span>

                        {showBadge && (
                          <span className="flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-red-500/15 text-red-400 text-xs font-bold tabular-nums">
                            {errorCount > 99 ? "99+" : errorCount}
                          </span>
                        )}
                        {showSignalBadge && (
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500" />
                          </span>
                        )}

                        {!showBadge && !showSignalBadge && (
                          <span className="text-xs font-mono text-sidebar-foreground/50 group-hover:text-sidebar-foreground/70 transition-colors">
                            {formatHotkey(item.hotkey)}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Session stats */}
      {isRunning && (
        <div className="mx-3 mb-2 p-3 rounded-lg bg-sidebar-muted/25 border border-sidebar-border/15">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-sidebar-foreground/70 mb-2">
            Session
          </p>
          {/* P&L prominent */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-sidebar-foreground/80 font-semibold">P&L</span>
            <span className={cn(
              "text-lg font-bold font-mono tabular-nums",
              dailyPnl.total > 0 ? "text-emerald-400 metric-profit" : dailyPnl.total < 0 ? "text-red-400 metric-loss" : "text-sidebar-foreground/40"
            )}>
              {dailyPnl.total >= 0 ? "+" : ""}${dailyPnl.total.toFixed(2)}
            </span>
          </div>
          <div className="grid grid-cols-5 gap-1 text-center">
            <div className="py-1 rounded bg-sidebar-muted/20">
              <p className="text-[13px] font-bold text-sidebar-foreground tabular-nums">{openTrades}</p>
              <p className="text-[10px] text-sidebar-foreground/70 font-medium">Open</p>
            </div>
            <div className="py-1 rounded bg-sidebar-muted/20">
              <p className="text-[13px] font-bold text-sidebar-foreground tabular-nums">{closedTrades}</p>
              <p className="text-[10px] text-sidebar-foreground/70 font-medium">Closed</p>
            </div>
            <div className="py-1 rounded bg-sidebar-muted/20">
              <p className="text-sm font-bold text-emerald-400 tabular-nums">{winningTrades}</p>
              <p className="text-[10px] text-sidebar-foreground/70 font-medium">Win</p>
            </div>
            <div className="py-1 rounded bg-sidebar-muted/20">
              <p className="text-sm font-bold text-red-400 tabular-nums">{losingTrades}</p>
              <p className="text-[10px] text-sidebar-foreground/70 font-medium">Loss</p>
            </div>
            <div className="py-1 rounded bg-sidebar-muted/20">
              <p className="text-sm font-bold text-sidebar-foreground/90 tabular-nums">{winRate}%</p>
              <p className="text-[10px] text-sidebar-foreground/70 font-medium">Rate</p>
            </div>
          </div>
        </div>
      )}

      {/* Footer status cards */}
      <div className="px-3 pb-3 space-y-1.5">
        {/* Connection status */}
        <div
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[12px] transition-colors",
            connectedToTws
              ? "bg-emerald-500/8 text-emerald-400 border border-emerald-500/10"
              : "bg-red-500/8 text-red-400 border border-red-500/10"
          )}
        >
          {connectedToTws ? (
            <Wifi className="h-4 w-4" />
          ) : (
            <WifiOff className="h-4 w-4" />
          )}
          <div className="flex-1 flex flex-col">
            <span className="font-semibold">
              {connectedToTws ? "TWS Connected" : "TWS Disconnected"}
            </span>
            {isRunning && connectedToTws && (
              <span className="text-xs text-emerald-400/70 flex items-center gap-1.5 mt-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 live-dot" />
                Engine active
              </span>
            )}
            {!connectedToTws && isRunning && (
              <span className="text-xs text-red-400/70 flex items-center gap-1.5 mt-0.5">
                <AlertCircle className="h-3 w-3" />
                Reconnecting…
              </span>
            )}
          </div>
        </div>

        {/* License */}
        {daysLeft !== null && (
          <div className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-[12px]",
            daysLeft <= 7 ? "bg-amber-500/8 text-amber-400 border border-amber-500/10" : "bg-emerald-500/5 text-emerald-400/60"
          )}>
            <Shield className="h-3.5 w-3.5" />
            <span className="font-semibold tabular-nums">{daysLeft}d remaining</span>
          </div>
        )}

        {/* Trading Mode */}
        <div
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[12px]",
            isLive
              ? "bg-red-500/10 text-red-400 border border-red-500/15"
              : "bg-sidebar-muted/25 text-sidebar-foreground/40"
          )}
        >
          <Zap className="h-3.5 w-3.5" />
          <span className="font-bold tracking-wider text-[13px]">
            {isLive ? "LIVE" : "DEMO"}
          </span>
          {isLive && (
            <span className="ml-auto h-2 w-2 rounded-full bg-red-400 live-dot" />
          )}
        </div>

        {/* User profile */}
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-[12px] text-sidebar-foreground/40 border-t border-sidebar-border/15 mt-2 pt-2">
          <div className="h-7 w-7 rounded-full bg-sidebar-muted/40 flex items-center justify-center">
            <User className="h-3.5 w-3.5 text-sidebar-foreground/35" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-sidebar-foreground/85 truncate">Trader</p>
            <p className="text-xs text-sidebar-foreground/60">v1.0</p>
          </div>
          <ChevronRight className="h-3.5 w-3.5 text-sidebar-foreground/15" />
        </div>
      </div>
    </aside>
  );
}

export const Sidebar = memo(SidebarInner);
