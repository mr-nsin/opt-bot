import { useRef, useEffect, useMemo, useState, memo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LogFilter } from "./LogFilter";
import { useLogStore } from "@/stores/logStore";
import { logs as logsApi } from "@/lib/tauri-commands";
import { cn, formatTime } from "@/lib/utils";
import {
  Trash2,
  ArrowDown,
  Terminal,
  AlertTriangle,
  Info,
  XCircle,
  Bug,
  Zap,
  ShoppingCart,
  Database,
  Settings2,
  Search,
  Target,
  ShieldAlert,
  Activity,
  RadioTower,
  Copy,
  Check,
} from "lucide-react";

const ROW_HEIGHT = 26;

const levelConfig: Record<
  string,
  {
    color: string;
    icon: typeof Info;
    bg: string;
    badgeVariant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "danger";
  }
> = {
  INFO: { color: "text-blue-500", icon: Info, bg: "bg-blue-500/5", badgeVariant: "default" },
  WARN: { color: "text-amber-500", icon: AlertTriangle, bg: "bg-amber-500/5 border-l-2 border-l-amber-500/40", badgeVariant: "warning" },
  ERROR: { color: "text-red-500", icon: XCircle, bg: "bg-red-500/5 border-l-2 border-l-red-500/40", badgeVariant: "danger" },
  DEBUG: { color: "text-muted-foreground/50", icon: Bug, bg: "bg-muted/20", badgeVariant: "secondary" },
};

const categoryConfig: Record<string, { icon: typeof Info; color: string; label: string }> = {
  signal: { icon: Target, color: "text-violet-400", label: "Signal" },
  order: { icon: ShoppingCart, color: "text-emerald-400", label: "Order" },
  orders: { icon: ShoppingCart, color: "text-emerald-400", label: "Order" },
  position: { icon: Activity, color: "text-cyan-400", label: "Position" },
  risk: { icon: ShieldAlert, color: "text-amber-400", label: "Risk" },
  trading: { icon: Zap, color: "text-violet-400", label: "Trading" },
  data: { icon: Database, color: "text-cyan-400", label: "Data" },
  engine: { icon: Settings2, color: "text-blue-400", label: "Engine" },
  system: { icon: Terminal, color: "text-slate-400", label: "System" },
  protocol: { icon: RadioTower, color: "text-slate-400", label: "Protocol" },
  sidecar: { icon: Terminal, color: "text-slate-400", label: "Sidecar" },
};

const LOG_DISPLAY_LIMIT = 60;

export const LogsPage = memo(function LogsPage() {
  const { logs, filterLevel, filterCategory, autoScroll, setLogs, clearLogs, setAutoScroll } =
    useLogStore();
  const parentRef = useRef<HTMLDivElement>(null);
  const infoPopoverRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [logDirPath, setLogDirPath] = useState<string | null>(null);
  const [pathCopied, setPathCopied] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);

  useEffect(() => {
    logsApi
      .get(undefined, undefined, LOG_DISPLAY_LIMIT)
      .then((entries) => {
        requestAnimationFrame(() => setLogs(entries));
      })
      .catch(console.error);
  }, [setLogs]);

  useEffect(() => {
    logsApi.getLogsDir().then(setLogDirPath).catch(() => setLogDirPath(null));
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        infoOpen &&
        infoPopoverRef.current &&
        !infoPopoverRef.current.contains(e.target as Node)
      ) {
        setInfoOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [infoOpen]);

  const filtered = useMemo(
    () =>
      logs.filter((l) => {
        if (filterLevel && l.level !== filterLevel) return false;
        if (filterCategory && l.category !== filterCategory) return false;
        if (
          searchQuery &&
          !l.message.toLowerCase().includes(searchQuery.toLowerCase())
        )
          return false;
        return true;
      }),
    [logs, filterLevel, filterCategory, searchQuery]
  );

  const levelCounts = useMemo(() => {
    const counts: Record<string, number> = { INFO: 0, WARN: 0, ERROR: 0, DEBUG: 0 };
    for (const l of logs) {
      counts[l.level] = (counts[l.level] || 0) + 1;
    }
    return counts;
  }, [logs]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const l of logs) {
      const cat = l.category?.toLowerCase() || "system";
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [logs]);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  });

  useEffect(() => {
    if (!autoScroll || !parentRef.current) return;
    const id = requestAnimationFrame(() => {
      if (parentRef.current)
        parentRef.current.scrollTop = parentRef.current.scrollHeight;
    });
    return () => cancelAnimationFrame(id);
  }, [filtered.length, autoScroll]);

  const copyLogPath = () => {
    if (logDirPath) {
      navigator.clipboard.writeText(logDirPath);
      setPathCopied(true);
      setTimeout(() => setPathCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-2.5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Terminal className="h-5 w-5 text-primary/80" />
            System Logs
            <span className="relative inline-flex" ref={infoPopoverRef}>
              <button
                type="button"
                onClick={() => setInfoOpen(!infoOpen)}
                className="p-1 rounded-md hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
                title={logDirPath || "Click for log path & info"}
              >
                <Info className="h-4 w-4" />
              </button>
              {infoOpen && (
                <div
                  className="absolute left-0 top-full mt-1 z-50 rounded-lg border border-border bg-card shadow-lg p-4 space-y-3 min-w-[420px] max-w-[90vw]"
                >
                  <p className="text-2xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Log file location
                  </p>
                  {logDirPath ? (
                    <div className="flex items-start gap-2">
                      <code
                        className="text-xs font-mono flex-1 bg-muted/50 rounded px-2 py-2 break-all"
                        title={logDirPath}
                      >
                        {logDirPath}
                      </code>
                      <button
                        type="button"
                        onClick={copyLogPath}
                        className="shrink-0 p-1.5 rounded hover:bg-muted text-muted-foreground"
                      >
                        {pathCopied ? (
                          <Check className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  ) : (
                    <p className="text-2xs text-muted-foreground">Loading…</p>
                  )}
                  <p className="text-2xs text-muted-foreground">
                    Trading engine file logs may also be in{" "}
                    <code className="bg-muted/50 px-1 rounded">~/QuantDrift/logs</code> when
                    running the packaged app.
                  </p>
                  <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-2">
                    <p className="text-2xs text-amber-700 dark:text-amber-400 font-medium flex items-start gap-1.5">
                      <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
                      Do not delete the logs — they are needed for analysis.
                      Please share logs with the team if anything goes wrong.
                    </p>
                  </div>
                </div>
              )}
            </span>
          </h2>
          <p className="text-xs text-muted-foreground/60">
            Last {LOG_DISPLAY_LIMIT} entries · Trading engine and system log viewer
          </p>
        </div>
        <div className="flex gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoScroll(!autoScroll)}
            className="h-8 text-xs"
          >
            <ArrowDown className={cn("h-3 w-3 mr-1", autoScroll && "text-primary")} />
            Auto-scroll {autoScroll ? "ON" : "OFF"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              await logsApi.clear();
              clearLogs();
            }}
            className="h-8 text-xs"
          >
            <Trash2 className="h-3 w-3 mr-1" /> Clear
          </Button>
        </div>
      </div>

      {/* Level summary badges */}
      <div className="flex items-center gap-2">
        {Object.entries(levelCounts).map(([level, count]) => {
          const cfg = levelConfig[level];
          if (!cfg || count === 0) return null;
          const Icon = cfg.icon;
          return (
            <Badge key={level} variant={cfg.badgeVariant} className="text-2xs gap-1 cursor-default">
              <Icon className="h-3 w-3" />
              {level}: {count}
            </Badge>
          );
        })}
        <span className="w-px h-4 bg-border/40 mx-1" />
        {(["signal", "order", "position", "risk"] as const).map((cat) => {
          const count = categoryCounts[cat] || 0;
          if (count === 0) return null;
          const cfg = categoryConfig[cat];
          const CIcon = cfg.icon;
          return (
            <Badge
              key={cat}
              variant="outline"
              className={cn("text-2xs gap-1 cursor-default", cfg.color)}
            >
              <CIcon className="h-3 w-3" />
              {cfg.label}: {count}
            </Badge>
          );
        })}
        <div className="flex-1" />
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search logs…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-7 pr-2.5 rounded-xl border border-border/20 bg-muted/20 text-xs focus:outline-none focus:ring-1 focus:ring-ring w-48"
          />
        </div>
      </div>

      <LogFilter />

      <Card>
        <CardHeader className="py-2 flex flex-row items-center justify-between">
          <CardTitle className="text-2xs text-muted-foreground font-mono">
            {filtered.length} of {logs.length} entries
          </CardTitle>
          {searchQuery && (
            <Badge variant="outline" className="text-2xs">
              Search: &quot;{searchQuery}&quot;
            </Badge>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <div
            ref={parentRef}
            className="h-[calc(100vh-320px)] overflow-y-auto font-mono text-2xs"
          >
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <Terminal className="h-8 w-8 text-muted-foreground/20 mb-2" />
                <p className="text-center text-xs text-muted-foreground">No logs</p>
                {searchQuery && (
                  <p className="text-center text-2xs text-muted-foreground/50 mt-1">
                    No results for &quot;{searchQuery}&quot;
                  </p>
                )}
              </div>
            ) : (
              <div
                style={{
                  height: `${virtualizer.getTotalSize()}px`,
                  position: "relative",
                }}
                className="w-full"
              >
                {virtualizer.getVirtualItems().map((virtualRow) => {
                  const l = filtered[virtualRow.index];
                  const cfg = levelConfig[l.level] || levelConfig.INFO;
                  const catCfg =
                    categoryConfig[l.category?.toLowerCase()] || {
                      icon: Terminal,
                      color: "text-muted-foreground/30",
                      label: l.category || "—",
                    };
                  const LevelIcon = cfg.icon;
                  const CatIcon = catCfg.icon;

                  return (
                    <div
                      key={`${l.timestamp}-${virtualRow.index}`}
                      className={cn(
                        "absolute left-0 top-0 flex items-center gap-2 px-3 border-b border-border/15 hover:bg-muted/20 w-full transition-colors stripe-row",
                        cfg.bg
                      )}
                      style={{
                        height: ROW_HEIGHT,
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                    >
                      <span className="text-muted-foreground/40 shrink-0 w-7 text-right tabular-nums text-xs">
                        {virtualRow.index + 1}
                      </span>
                      <span className="text-muted-foreground/50 shrink-0 w-14 tabular-nums text-xs">
                        {formatTime(l.timestamp)}
                      </span>
                      <span className={cn("flex items-center gap-0.5 shrink-0 w-12", cfg.color)}>
                        <LevelIcon className="h-2.5 w-2.5" />
                        <span className="font-semibold text-xs">{l.level}</span>
                      </span>
                      <span className={cn("flex items-center gap-0.5 shrink-0 w-14", catCfg.color)}>
                        <CatIcon className="h-2.5 w-2.5" />
                        <span className="text-xs opacity-70">{catCfg.label}</span>
                      </span>
                      <span className="text-foreground/80 break-all flex-1 text-xs truncate">
                        {l.message}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
