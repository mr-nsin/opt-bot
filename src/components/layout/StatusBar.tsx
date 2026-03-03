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

export const StatusBar = memo(function StatusBar() {
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const status = useTradingStore((s) => s.status);
  const isSignalScanning = useTradingStore((s) => s.isSignalScanning);
  const dataStatus = useTradingStore((s) => s.dataStatus);
  const openTrades = useTradingStore((s) => s.openTrades);
  const closedTrades = useTradingStore((s) => s.closedTrades);
  const dailyPnl = useTradingStore((s) => s.dailyPnl);
  const logs = useLogStore((s) => s.logs);

  const isRunning = status === "Running";
  const isStarting = status === "Starting";
  const isError = typeof status === "object" && "Error" in status;

  const startTimeRef = useRef<number | null>(null);
  const [uptime, setUptime] = useState("");

  useEffect(() => {
    if (isRunning && !startTimeRef.current) startTimeRef.current = Date.now();
    if (!isRunning && status === "Idle") { startTimeRef.current = null; setUptime(""); }
  }, [isRunning, status]);

  useEffect(() => {
    if (!startTimeRef.current) return;
    const tick = () => {
      const diff = Math.floor((Date.now() - (startTimeRef.current ?? Date.now())) / 1000);
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setUptime(h > 0 ? `${h}h ${m.toString().padStart(2, "0")}m` : `${m}m ${s.toString().padStart(2, "0")}s`);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isRunning]);

  const errorCount = logs.filter((l) => l.level === "ERROR").length;
  const feedSymbols = (dataStatus as Record<string, unknown>)?.symbols;
  const feedCount = Array.isArray(feedSymbols) ? feedSymbols.length : 0;

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
    <div className="h-8 bg-card/80 backdrop-blur-sm border-t border-border/10 flex items-center justify-between px-3 text-xs shrink-0 select-none">
      {/* Left */}
      <div className="flex items-center gap-0.5">
        <SBItem
          icon={connectedToTws ? Wifi : WifiOff}
          label={connectedToTws ? "TWS" : "Disconnected"}
          color={connectedToTws ? "text-emerald-400" : "text-red-400"}
          bg={connectedToTws ? "hover:bg-emerald-500/5" : "hover:bg-red-500/5"}
        />
        <SBItem
          icon={Activity}
          label={isRunning ? "Running" : isStarting ? "Starting…" : isError ? "Error" : "Idle"}
          color={isRunning ? "text-emerald-400" : isStarting ? "text-amber-400" : isError ? "text-red-400" : "text-muted-foreground/40"}
          pulse={isStarting}
        />
        {isRunning && (
          <SBItem
            icon={Radio}
            label={isSignalScanning ? "Scanning" : "Idle"}
            color={isSignalScanning ? "text-violet-400" : "text-muted-foreground/30"}
            pulse={isSignalScanning}
          />
        )}
        {isRunning && (
          <SBItem
            icon={Database}
            label={feedCount > 0 ? `${feedCount} feeds` : "No feeds"}
            color={feedCount > 0 ? "text-cyan-400" : "text-muted-foreground/30"}
          />
        )}
        {errorCount > 0 && (
          <SBItem
            icon={AlertTriangle}
            label={`${errorCount} error${errorCount > 1 ? "s" : ""}`}
            color="text-red-400"
            bg="bg-red-500/5"
          />
        )}
      </div>

      {/* Center */}
      {isRunning && (
        <div className="flex items-center gap-3 text-muted-foreground/50">
            <span className="flex items-center gap-1">
            <Zap className="h-2.5 w-2.5" />
            <span className="font-mono tabular-nums">{openTrades} open / {closedTrades} closed</span>
          </span>
          <span className="text-border/30">·</span>
          <span
            className={cn(
              "font-mono tabular-nums font-semibold",
              dailyPnl.total > 0 ? "text-emerald-400/60" : dailyPnl.total < 0 ? "text-red-400/60" : "text-muted-foreground/30"
            )}
          >
            {dailyPnl.total >= 0 ? "+" : ""}${dailyPnl.total.toFixed(2)}
          </span>
        </div>
      )}

      {/* Right */}
      <div className="flex items-center">
        {uptime && <SBItem icon={Cpu} label={uptime} color="text-muted-foreground/50" />}
        <div className="flex items-center gap-1 px-2 h-full text-muted-foreground/45">
          <Clock className="h-2.5 w-2.5" />
          <span className="font-mono tabular-nums">{nyClock}</span>
          <span className="text-muted-foreground/25 ml-0.5">ET</span>
        </div>
      </div>
    </div>
  );
});

function SBItem({
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
    <div className={cn("flex items-center gap-1.5 px-2 h-8 transition-colors cursor-default rounded", bg)}>
      <Icon className={cn("h-3.5 w-3.5", color, pulse && "animate-pulse")} />
      <span className={cn("font-medium", color)}>{label}</span>
    </div>
  );
}
