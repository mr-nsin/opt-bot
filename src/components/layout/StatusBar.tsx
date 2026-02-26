import { memo, useEffect, useState, useRef } from "react";
import { useTradingStore } from "@/stores/tradingStore";
import { useLogStore } from "@/stores/logStore";
import { cn } from "@/lib/utils";
import {
  Wifi,
  WifiOff,
  Activity,
  Database,
  Clock,
  Cpu,
  Radio,
  AlertTriangle,
  Zap,
} from "lucide-react";

/**
 * StatusBar — A 24px bottom bar inspired by VS Code / NinjaTrader status bars.
 * Shows: connection status, engine state, data feed health, signal scanner,
 * error count, uptime, and clock.
 */
export const StatusBar = memo(function StatusBar() {
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const status = useTradingStore((s) => s.status);
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);
  const dataStatus = useTradingStore((s) => s.dataStatus);
  const totalTrades = useTradingStore((s) => s.totalTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const logs = useLogStore((s) => s.logs);

  const isRunning = status === "Running";
  const isStarting = status === "Starting";
  const isError = typeof status === "object" && "Error" in status;

  // Uptime counter
  const startTimeRef = useRef<number | null>(null);
  const [uptime, setUptime] = useState("");

  useEffect(() => {
    if (isRunning && !startTimeRef.current) {
      startTimeRef.current = Date.now();
    }
    if (!isRunning && status === "Idle") {
      startTimeRef.current = null;
      setUptime("");
    }
  }, [isRunning, status]);

  useEffect(() => {
    if (!startTimeRef.current) return;
    const tick = () => {
      const diff = Math.floor((Date.now() - (startTimeRef.current ?? Date.now())) / 1000);
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setUptime(
        h > 0
          ? `${h}h ${m.toString().padStart(2, "0")}m`
          : `${m}m ${s.toString().padStart(2, "0")}s`
      );
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isRunning]);

  // Error count
  const errorCount = logs.filter((l) => l.level === "ERROR").length;

  // Data feed info
  const feedSymbols = (dataStatus as Record<string, unknown>)?.subscribed_symbols;
  const feedCount = Array.isArray(feedSymbols) ? feedSymbols.length : 0;

  // NY clock
  const [nyClock, setNyClock] = useState("");
  useEffect(() => {
    const tick = () => {
      setNyClock(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "America/New_York",
        })
      );
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="h-6 bg-card/90 backdrop-blur-sm border-t border-border/50 flex items-center justify-between px-2 text-2xs shrink-0 select-none">
      {/* Left section */}
      <div className="flex items-center gap-0">
        {/* Connection status */}
        <StatusItem
          icon={connectedToTws ? Wifi : WifiOff}
          label={connectedToTws ? "TWS" : "Disconnected"}
          color={connectedToTws ? "text-emerald-500" : "text-red-500"}
          bg={connectedToTws ? "bg-emerald-500/8" : "bg-red-500/8"}
        />

        {/* Engine status */}
        <StatusItem
          icon={Activity}
          label={
            isRunning
              ? "Running"
              : isStarting
                ? "Starting…"
                : isError
                  ? "Error"
                  : "Idle"
          }
          color={
            isRunning
              ? "text-emerald-500"
              : isStarting
                ? "text-amber-500"
                : isError
                  ? "text-red-500"
                  : "text-muted-foreground/50"
          }
          bg={isRunning ? "bg-emerald-500/5" : ""}
          pulse={isStarting}
        />

        {/* Signal scanner */}
        {isRunning && (
          <StatusItem
            icon={Radio}
            label={isSignalScanning ? "Scanning" : "Idle"}
            color={isSignalScanning ? "text-violet-400" : "text-muted-foreground/40"}
            pulse={isSignalScanning}
          />
        )}

        {/* Data feed */}
        {isRunning && (
          <StatusItem
            icon={Database}
            label={feedCount > 0 ? `${feedCount} feeds` : "No feeds"}
            color={feedCount > 0 ? "text-cyan-500" : "text-muted-foreground/40"}
          />
        )}

        {/* Error badge */}
        {errorCount > 0 && (
          <StatusItem
            icon={AlertTriangle}
            label={`${errorCount} error${errorCount > 1 ? "s" : ""}`}
            color="text-red-400"
            bg="bg-red-500/8"
          />
        )}
      </div>

      {/* Center: quick stats when running */}
      {isRunning && (
        <div className="flex items-center gap-3 text-muted-foreground/60">
          <span className="flex items-center gap-1">
            <Zap className="h-2.5 w-2.5" />
            <span className="font-mono tabular-nums">{totalTrades} trades</span>
          </span>
          <span className="text-border/40">·</span>
          <span
            className={cn(
              "font-mono tabular-nums font-semibold",
              dailyPnl.total > 0
                ? "text-emerald-500/70"
                : dailyPnl.total < 0
                  ? "text-red-500/70"
                  : "text-muted-foreground/40"
            )}
          >
            {dailyPnl.total >= 0 ? "+" : ""}${dailyPnl.total.toFixed(2)}
          </span>
        </div>
      )}

      {/* Right section */}
      <div className="flex items-center gap-0">
        {/* Uptime */}
        {uptime && (
          <StatusItem
            icon={Cpu}
            label={uptime}
            color="text-muted-foreground/60"
          />
        )}

        {/* NY Clock */}
        <div className="flex items-center gap-1 px-2 h-full text-muted-foreground/50">
          <Clock className="h-2.5 w-2.5" />
          <span className="font-mono tabular-nums">{nyClock}</span>
          <span className="text-muted-foreground/30">ET</span>
        </div>
      </div>
    </div>
  );
});

/** Small status bar item with icon + label */
function StatusItem({
  icon: Icon,
  label,
  color,
  bg,
  pulse,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bg?: string;
  pulse?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 px-2 h-6 transition-colors cursor-default hover:bg-muted/30",
        bg
      )}
    >
      <Icon className={cn("h-2.5 w-2.5", color, pulse && "animate-pulse")} />
      <span className={cn("font-medium", color)}>{label}</span>
    </div>
  );
}
