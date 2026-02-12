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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/stores/tradingStore";
import { useConfigStore } from "@/stores/configStore";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { id: "analytics", label: "Analytics", icon: BarChart3, path: "/analytics" },
  { id: "positions", label: "Positions", icon: Briefcase, path: "/positions" },
  { id: "logs", label: "Logs", icon: FileText, path: "/logs" },
  { id: "settings", label: "Settings", icon: Settings, path: "/settings" },
];

export function Sidebar() {
  const { connectedToTws, status } = useTradingStore();
  const { settings } = useConfigStore();
  const isRunning = status === "Running";
  const isLive = settings.trading_mode === "live";

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
                  {isActive && (
                    <ChevronRight className="h-3.5 w-3.5 text-sidebar-accent/50" />
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer: Connection + Mode */}
      <div className="px-3 pb-3 space-y-2">
        {/* Connection Status */}
        <div
          className={cn(
            "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs",
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
          </div>
        </div>

        {/* Trading Mode */}
        <div
          className={cn(
            "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs",
            isLive
              ? "bg-red-500/10 text-red-400"
              : "bg-sidebar-muted text-sidebar-foreground/50"
          )}
        >
          <Shield className="h-3.5 w-3.5" />
          <span className="font-medium">
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
