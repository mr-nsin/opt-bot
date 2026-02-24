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
} from "lucide-react";

const ROW_HEIGHT = 30;

const levelConfig: Record<string, { color: string; icon: typeof Info; bg: string; badgeVariant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "danger" }> = {
  INFO: { color: "text-blue-400", icon: Info, bg: "", badgeVariant: "default" },
  WARN: { color: "text-amber-400", icon: AlertTriangle, bg: "bg-amber-500/3", badgeVariant: "warning" },
  ERROR: { color: "text-red-400", icon: XCircle, bg: "bg-red-500/5 border-l-2 border-l-red-500/30", badgeVariant: "danger" },
  DEBUG: { color: "text-muted-foreground/40", icon: Bug, bg: "", badgeVariant: "secondary" },
};

const categoryConfig: Record<string, { icon: typeof Info; color: string }> = {
  trading: { icon: Zap, color: "text-violet-400" },
  order: { icon: ShoppingCart, color: "text-emerald-400" },
  orders: { icon: ShoppingCart, color: "text-emerald-400" },
  data: { icon: Database, color: "text-cyan-400" },
  engine: { icon: Settings2, color: "text-blue-400" },
  signal: { icon: Zap, color: "text-violet-400" },
  system: { icon: Terminal, color: "text-slate-400" },
};

export const LogsPage = memo(function LogsPage() {
  const { logs, filterLevel, filterCategory, autoScroll, setLogs, clearLogs, setAutoScroll } = useLogStore();
  const parentRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    logsApi.get(undefined, undefined, 500).then(setLogs).catch(console.error);
  }, [setLogs]);

  const filtered = useMemo(
    () =>
      logs.filter((l) => {
        if (filterLevel && l.level !== filterLevel) return false;
        if (filterCategory && l.category !== filterCategory) return false;
        if (searchQuery && !l.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
      }),
    [logs, filterLevel, filterCategory, searchQuery]
  );

  // Level counts for summary
  const levelCounts = useMemo(() => {
    const counts: Record<string, number> = { INFO: 0, WARN: 0, ERROR: 0, DEBUG: 0 };
    for (const l of logs) {
      counts[l.level] = (counts[l.level] || 0) + 1;
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
    if (autoScroll && parentRef.current) {
      parentRef.current.scrollTop = parentRef.current.scrollHeight;
    }
  }, [filtered.length, autoScroll]);

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <Terminal className="h-5 w-5 text-muted-foreground" />
            System Logs
          </h2>
          <p className="text-xs text-muted-foreground">Trading engine and system log viewer</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAutoScroll(!autoScroll)}>
            <ArrowDown className={cn("h-3.5 w-3.5 mr-1.5", autoScroll && "text-primary")} />
            Auto-scroll {autoScroll ? "ON" : "OFF"}
          </Button>
          <Button variant="outline" size="sm" onClick={async () => { await logsApi.clear(); clearLogs(); }}>
            <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Clear
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
            <Badge
              key={level}
              variant={cfg.badgeVariant}
              className="text-2xs gap-1 cursor-default"
            >
              <Icon className="h-3 w-3" />
              {level}: {count}
            </Badge>
          );
        })}
        <div className="flex-1" />
        {/* Inline search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="Search logs…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 pr-3 rounded-md border border-border/50 bg-muted/30 text-xs focus:outline-none focus:ring-2 focus:ring-ring w-56"
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
              Search: "{searchQuery}"
            </Badge>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <div ref={parentRef} className="h-[calc(100vh-320px)] overflow-y-auto font-mono text-2xs">
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <Terminal className="h-8 w-8 text-muted-foreground/20 mb-2" />
                <p className="text-center text-xs text-muted-foreground">No logs</p>
                {searchQuery && (
                  <p className="text-center text-2xs text-muted-foreground/50 mt-1">
                    No results for "{searchQuery}"
                  </p>
                )}
              </div>
            ) : (
              <div
                style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
                className="w-full"
              >
                {virtualizer.getVirtualItems().map((virtualRow) => {
                  const l = filtered[virtualRow.index];
                  const cfg = levelConfig[l.level] || levelConfig.INFO;
                  const catCfg = categoryConfig[l.category?.toLowerCase()] || { icon: Terminal, color: "text-muted-foreground/30" };
                  const LevelIcon = cfg.icon;
                  const CatIcon = catCfg.icon;

                  return (
                    <div
                      key={`${l.timestamp}-${virtualRow.index}`}
                      className={cn(
                        "absolute left-0 top-0 flex items-center gap-2.5 px-4 border-b border-border/20 hover:bg-muted/30 w-full transition-colors",
                        cfg.bg
                      )}
                      style={{ height: ROW_HEIGHT, transform: `translateY(${virtualRow.start}px)` }}
                    >
                      {/* Row number */}
                      <span className="text-muted-foreground/20 shrink-0 w-8 text-right tabular-nums">
                        {virtualRow.index + 1}
                      </span>

                      {/* Timestamp */}
                      <span className="text-muted-foreground/40 shrink-0 w-16 tabular-nums">
                        {formatTime(l.timestamp)}
                      </span>

                      {/* Level icon + label */}
                      <span className={cn("flex items-center gap-1 shrink-0 w-14", cfg.color)}>
                        <LevelIcon className="h-3 w-3" />
                        <span className="font-semibold">{l.level}</span>
                      </span>

                      {/* Category icon + label */}
                      <span className={cn("flex items-center gap-1 shrink-0 w-16", catCfg.color)}>
                        <CatIcon className="h-3 w-3" />
                        <span className="text-2xs opacity-70">{l.category || "—"}</span>
                      </span>

                      {/* Message */}
                      <span className="text-foreground/70 break-all flex-1">
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
