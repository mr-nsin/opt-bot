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
  ChevronRight,
  Wifi,
  WifiOff,
  AlertCircle,
  Zap,
} from "lucide-react";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useLicense } from "@/hooks/useLicense";
import { formatHotkey } from "@/hooks/useHotkeys";

// Navigation organized into groups (like NinjaTrader/TradingView)
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
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);
  const settings = useConfigStore((s) => s.settings);
  const logs = useLogStore((s) => s.logs);
  const { licenseStatus } = useLicense();
  const isRunning = status === "Running";
  const isLive = settings.trading_mode === "live";
  const daysLeft = licenseStatus?.valid ? licenseStatus.days_remaining : null;

  const errorCount = useMemo(
    () => logs.filter((l) => l.level === "ERROR").length,
    [logs]
  );

  return (
    <aside className="w-[210px] bg-sidebar flex flex-col border-r border-sidebar-border shrink-0">
      {/* Brand */}
      <div className="h-11 flex items-center gap-2.5 px-4 border-b border-sidebar-border">
        <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
          <Activity className="h-3.5 w-3.5 text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-xs font-bold text-sidebar-foreground tracking-tight">
            QuantDrift
          </span>
          <span className="text-2xs text-sidebar-foreground/40">
            Trading Terminal
          </span>
        </div>
      </div>

      {/* Navigation groups */}
      <nav className="flex-1 px-2.5 py-3 space-y-3 overflow-y-auto">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="text-2xs font-semibold uppercase tracking-widest text-sidebar-foreground/25 px-2.5 mb-1">
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
                        "flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[12px] font-medium transition-colors group relative",
                        isActive
                          ? "bg-sidebar-accent/10 text-sidebar-accent"
                          : "text-sidebar-foreground/50 hover:text-sidebar-foreground hover:bg-sidebar-muted/50"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 rounded-r-full bg-sidebar-accent" />
                        )}
                        <Icon
                          className={cn(
                            "h-[15px] w-[15px] shrink-0",
                            isActive
                              ? "text-sidebar-accent"
                              : "text-sidebar-foreground/35 group-hover:text-sidebar-foreground/50"
                          )}
                        />
                        <span className="flex-1">{item.label}</span>

                        {/* Badges */}
                        {showBadge && (
                          <span className="flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-red-500/20 text-red-400 text-2xs font-bold tabular-nums">
                            {errorCount > 99 ? "99+" : errorCount}
                          </span>
                        )}
                        {showSignalBadge && (
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-violet-500" />
                          </span>
                        )}

                        {/* Hotkey hint (visible on hover) */}
                        {!showBadge && !showSignalBadge && (
                          <span className="text-2xs font-mono text-sidebar-foreground/15 group-hover:text-sidebar-foreground/30 transition-colors">
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

      {/* Session stats (compact) */}
      {isRunning && (
        <div className="mx-2.5 mb-2 p-2 rounded-md bg-sidebar-muted/30 border border-sidebar-border/30">
          <p className="text-2xs font-semibold uppercase tracking-widest text-sidebar-foreground/25 mb-1.5">
            Session
          </p>
          {/* P&L prominent */}
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-2xs text-sidebar-foreground/40">P&L</span>
            <span className={cn(
              "text-xs font-bold font-mono tabular-nums",
              dailyPnl.total > 0 ? "text-emerald-400" : dailyPnl.total < 0 ? "text-red-400" : "text-sidebar-foreground/40"
            )}>
              {dailyPnl.total >= 0 ? "+" : ""}${dailyPnl.total.toFixed(2)}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1 text-center">
            <div>
              <p className="text-2xs font-bold text-sidebar-foreground tabular-nums">{totalTrades}</p>
              <p className="text-2xs text-sidebar-foreground/30">Trades</p>
            </div>
            <div>
              <p className="text-2xs font-bold text-emerald-400 tabular-nums">{winningTrades}</p>
              <p className="text-2xs text-sidebar-foreground/30">W</p>
            </div>
            <div>
              <p className="text-2xs font-bold text-red-400 tabular-nums">{losingTrades}</p>
              <p className="text-2xs text-sidebar-foreground/30">L</p>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-2.5 pb-2.5 space-y-1.5">
        {/* Connection */}
        <div
          className={cn(
            "flex items-center gap-2 px-2.5 py-2 rounded-md text-2xs transition-colors",
            connectedToTws
              ? "bg-emerald-500/8 text-emerald-400"
              : "bg-red-500/8 text-red-400"
          )}
        >
          {connectedToTws ? (
            <Wifi className="h-3 w-3" />
          ) : (
            <WifiOff className="h-3 w-3" />
          )}
          <div className="flex-1 flex flex-col">
            <span className="font-medium">
              {connectedToTws ? "TWS Connected" : "TWS Disconnected"}
            </span>
            {isRunning && connectedToTws && (
              <span className="text-2xs text-emerald-400/60 flex items-center gap-1">
                <span className="h-1 w-1 rounded-full bg-emerald-400 live-dot" />
                Engine running
              </span>
            )}
            {!connectedToTws && isRunning && (
              <span className="text-2xs text-red-400/60 flex items-center gap-1">
                <AlertCircle className="h-2 w-2" />
                Reconnecting…
              </span>
            )}
          </div>
        </div>

        {/* License */}
        {daysLeft !== null && (
          <div className={cn(
            "flex items-center gap-2 px-2.5 py-1.5 rounded-md text-2xs",
            daysLeft <= 7 ? "bg-amber-500/8 text-amber-400" : "bg-emerald-500/5 text-emerald-400/70"
          )}>
            <Shield className="h-3 w-3" />
            <span className="font-medium tabular-nums">{daysLeft}d left</span>
          </div>
        )}

        {/* Trading Mode */}
        <div
          className={cn(
            "flex items-center gap-2 px-2.5 py-1.5 rounded-md text-2xs",
            isLive
              ? "bg-red-500/10 text-red-400 border border-red-500/15"
              : "bg-sidebar-muted/30 text-sidebar-foreground/40"
          )}
        >
          <Zap className="h-3 w-3" />
          <span className="font-bold tracking-wider">
            {isLive ? "LIVE" : "DEMO"}
          </span>
          {isLive && (
            <span className="ml-auto h-1.5 w-1.5 rounded-full bg-red-400 live-dot" />
          )}
        </div>
      </div>
    </aside>
  );
}

export const Sidebar = memo(SidebarInner);
