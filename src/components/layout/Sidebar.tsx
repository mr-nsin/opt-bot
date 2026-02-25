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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";
import { useLogStore } from "@/stores/logStore";
import { useLicense } from "@/hooks/useLicense";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { id: "analytics", label: "Analytics", icon: BarChart3, path: "/analytics" },
  { id: "positions", label: "Positions", icon: Briefcase, path: "/positions" },
  { id: "logs", label: "Logs", icon: FileText, path: "/logs" },
  { id: "settings", label: "Settings", icon: Settings, path: "/settings" },
];

function SidebarInner() {
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const status = useTradingStore((s) => s.status);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const winningTrades = useTradingStore((s) => s.winningTrades);
  const losingTrades = useTradingStore((s) => s.losingTrades);
  const settings = useConfigStore((s) => s.settings);
  const logs = useLogStore((s) => s.logs);
  const { licenseStatus } = useLicense();
  const isRunning = status === "Running";
  const isLive = settings.trading_mode === "live";
  const daysLeft = licenseStatus?.valid ? licenseStatus.days_remaining : null;

  // Count recent errors for badge on Logs nav item
  const errorCount = useMemo(
    () => logs.filter((l) => l.level === "ERROR").length,
    [logs]
  );

  // Signal scanning state from the store (set by engine heartbeat logs)
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);

  return (
    <aside className="w-[220px] bg-sidebar flex flex-col border-r border-sidebar-border shrink-0">
      {/* Brand */}
      <div className="h-14 flex items-center gap-2.5 px-5 border-b border-sidebar-border">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
          <Activity className="h-4 w-4 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold text-sidebar-foreground tracking-tight">
            QuantDrift
          </span>
          <span className="text-2xs text-sidebar-foreground/50">
            Options Trading
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="text-2xs font-semibold uppercase tracking-widest text-sidebar-foreground/30 px-3 mb-2">
          Menu
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          const showBadge = item.id === "logs" && errorCount > 0;
          const showSignalBadge = item.id === "dashboard" && isSignalScanning && isRunning;

          return (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors group relative",
                  isActive
                    ? "bg-sidebar-accent/10 text-sidebar-accent"
                    : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-muted"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-sidebar-accent" />
                  )}
                  <Icon
                    className={cn(
                      "h-[18px] w-[18px] shrink-0",
                      isActive
                        ? "text-sidebar-accent"
                        : "text-sidebar-foreground/40 group-hover:text-sidebar-foreground/60"
                    )}
                  />
                  <span className="flex-1">{item.label}</span>
                  {/* Error count badge for Logs */}
                  {showBadge && (
                    <span className="flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-red-500/20 text-red-400 text-2xs font-bold tabular-nums">
                      {errorCount > 99 ? "99+" : errorCount}
                    </span>
                  )}
                  {/* Signal/Order activity dot for Dashboard when engine is running */}
                  {showSignalBadge && (
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500" />
                    </span>
                  )}
                  {isActive && !showBadge && (
                    <ChevronRight className="h-3.5 w-3.5 text-sidebar-accent/50" />
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Session mini-stats */}
      {isRunning && totalTrades > 0 && (
        <div className="mx-3 mb-2 p-2.5 rounded-lg bg-sidebar-muted/50 border border-sidebar-border/50">
          <p className="text-2xs font-semibold uppercase tracking-widest text-sidebar-foreground/30 mb-1.5">
            Session
          </p>
          <div className="grid grid-cols-3 gap-1 text-center">
            <div>
              <p className="text-xs font-bold text-sidebar-foreground tabular-nums">{totalTrades}</p>
              <p className="text-2xs text-sidebar-foreground/40">Trades</p>
            </div>
            <div>
              <p className="text-xs font-bold text-emerald-400 tabular-nums">{winningTrades}</p>
              <p className="text-2xs text-sidebar-foreground/40">Wins</p>
            </div>
            <div>
              <p className="text-xs font-bold text-red-400 tabular-nums">{losingTrades}</p>
              <p className="text-2xs text-sidebar-foreground/40">Losses</p>
            </div>
          </div>
        </div>
      )}

      {/* Footer: Connection + Mode */}
      <div className="px-3 pb-3 space-y-2">
        {/* Connection Status */}
        <div
          className={cn(
            "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs transition-colors",
            connectedToTws
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          )}
        >
          {connectedToTws ? (
            <Wifi className="h-3.5 w-3.5" />
          ) : (
            <WifiOff className="h-3.5 w-3.5" />
          )}
          <div className="flex-1 flex flex-col">
            <span className="font-medium">
              {connectedToTws ? "TWS Connected" : "TWS Disconnected"}
            </span>
            {isRunning && (
              <span className="text-2xs text-emerald-400/70 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 live-dot" />
                Engine running
              </span>
            )}
            {!connectedToTws && isRunning && (
              <span className="text-2xs text-red-400/70 flex items-center gap-1">
                <AlertCircle className="h-2.5 w-2.5" />
                Reconnecting…
              </span>
            )}
          </div>
        </div>

        {/* License: days left */}
        {daysLeft !== null && (
          <div className={cn(
            "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs",
            daysLeft <= 7 ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
          )}>
            <Shield className="h-3.5 w-3.5" />
            <span className="font-medium tabular-nums">{daysLeft} days left</span>
            {daysLeft <= 7 && <span className="text-amber-400 text-2xs font-semibold">(expiring)</span>}
          </div>
        )}

        {/* Trading Mode */}
        <div
          className={cn(
            "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs",
            isLive
              ? "bg-red-500/10 text-red-400 border border-red-500/20"
              : "bg-sidebar-muted text-sidebar-foreground/50"
          )}
        >
          <Shield className="h-3.5 w-3.5" />
          <span className="font-bold tracking-wider">
            {isLive ? "LIVE TRADING" : "DEMO MODE"}
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
