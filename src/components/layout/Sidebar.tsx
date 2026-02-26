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
} from "lucide-react";
import { cn, pnlColor } from "@/lib/utils";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";
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

  const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(0) : "—";

  return (
    <aside className="w-[190px] sidebar-pro flex flex-col border-r border-sidebar-border/40 shrink-0">
      {/* Brand */}
      <div className="h-10 flex items-center gap-2 px-3 border-b border-sidebar-border/25">
        <div className="h-6 w-6 rounded-md bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
          <Activity className="h-3 w-3 text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[11px] font-bold text-sidebar-foreground tracking-tight">
            QuantDrift
          </span>
          <span className="text-[9px] text-sidebar-foreground/30 font-medium">
            Trading Terminal
          </span>
        </div>
      </div>

      {/* Navigation groups */}
      <nav className="flex-1 px-2 py-2.5 space-y-2.5 overflow-y-auto">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/20 px-2.5 mb-1">
              {group.label}
            </p>
            <div className="space-y-px">
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
                        "flex items-center gap-2 px-2.5 py-[5px] rounded-md text-[11px] font-medium transition-all group relative",
                        isActive
                          ? "bg-sidebar-accent/12 text-sidebar-accent"
                          : "text-sidebar-foreground/45 hover:text-sidebar-foreground/70 hover:bg-sidebar-muted/40"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-3.5 rounded-r-full bg-sidebar-accent" />
                        )}
                        <Icon
                          className={cn(
                            "h-3.5 w-3.5 shrink-0",
                            isActive
                              ? "text-sidebar-accent"
                              : "text-sidebar-foreground/30 group-hover:text-sidebar-foreground/45"
                          )}
                        />
                        <span className="flex-1">{item.label}</span>

                        {showBadge && (
                          <span className="flex items-center justify-center h-3.5 min-w-[14px] px-0.5 rounded-full bg-red-500/20 text-red-400 text-[9px] font-bold tabular-nums">
                            {errorCount > 99 ? "99+" : errorCount}
                          </span>
                        )}
                        {showSignalBadge && (
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-violet-500" />
                          </span>
                        )}

                        {!showBadge && !showSignalBadge && (
                          <span className="text-[9px] font-mono text-sidebar-foreground/12 group-hover:text-sidebar-foreground/25 transition-colors">
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
        <div className="mx-2 mb-1.5 p-2 rounded-md bg-sidebar-muted/20 border border-sidebar-border/20">
          <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/20 mb-1.5">
            Session
          </p>
          {/* P&L prominent */}
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[9px] text-sidebar-foreground/35">P&L</span>
            <span className={cn(
              "text-[13px] font-bold font-mono tabular-nums",
              dailyPnl.total > 0 ? "text-emerald-400" : dailyPnl.total < 0 ? "text-red-400" : "text-sidebar-foreground/35"
            )}>
              {dailyPnl.total >= 0 ? "+" : ""}${dailyPnl.total.toFixed(2)}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-0.5 text-center">
            <div>
              <p className="text-[10px] font-bold text-sidebar-foreground tabular-nums">{totalTrades}</p>
              <p className="text-[8px] text-sidebar-foreground/25">Total</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-emerald-400 tabular-nums">{winningTrades}</p>
              <p className="text-[8px] text-sidebar-foreground/25">Win</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-red-400 tabular-nums">{losingTrades}</p>
              <p className="text-[8px] text-sidebar-foreground/25">Loss</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-sidebar-foreground/70 tabular-nums">{winRate}%</p>
              <p className="text-[8px] text-sidebar-foreground/25">Rate</p>
            </div>
          </div>
        </div>
      )}

      {/* Footer status cards */}
      <div className="px-2 pb-2 space-y-1">
        {/* Connection status */}
        <div
          className={cn(
            "flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[10px] transition-colors",
            connectedToTws
              ? "bg-emerald-500/6 text-emerald-400"
              : "bg-red-500/6 text-red-400"
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
              <span className="text-[9px] text-emerald-400/50 flex items-center gap-1">
                <span className="h-1 w-1 rounded-full bg-emerald-400 live-dot" />
                Engine active
              </span>
            )}
            {!connectedToTws && isRunning && (
              <span className="text-[9px] text-red-400/50 flex items-center gap-1">
                <AlertCircle className="h-2 w-2" />
                Reconnecting…
              </span>
            )}
          </div>
        </div>

        {/* License */}
        {daysLeft !== null && (
          <div className={cn(
            "flex items-center gap-2 px-2.5 py-1 rounded-md text-[10px]",
            daysLeft <= 7 ? "bg-amber-500/6 text-amber-400" : "bg-emerald-500/4 text-emerald-400/60"
          )}>
            <Shield className="h-2.5 w-2.5" />
            <span className="font-medium tabular-nums">{daysLeft}d remaining</span>
          </div>
        )}

        {/* Trading Mode */}
        <div
          className={cn(
            "flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[10px]",
            isLive
              ? "bg-red-500/8 text-red-400 border border-red-500/12"
              : "bg-sidebar-muted/20 text-sidebar-foreground/35"
          )}
        >
          <Zap className="h-2.5 w-2.5" />
          <span className="font-bold tracking-wider">
            {isLive ? "LIVE" : "DEMO"}
          </span>
          {isLive && (
            <span className="ml-auto h-1.5 w-1.5 rounded-full bg-red-400 live-dot" />
          )}
        </div>

        {/* User profile badge (Trabot-style) */}
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[10px] text-sidebar-foreground/35 border-t border-sidebar-border/15 mt-1 pt-1.5">
          <div className="h-5 w-5 rounded-full bg-sidebar-muted/40 flex items-center justify-center">
            <User className="h-2.5 w-2.5 text-sidebar-foreground/30" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-medium text-sidebar-foreground/50 truncate">Trader</p>
            <p className="text-[8px] text-sidebar-foreground/20">v1.0</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export const Sidebar = memo(SidebarInner);
