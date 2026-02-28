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
} from "lucide-react";

const ROW_HEIGHT = 26;

const levelConfig: Record<string, { color: string; icon: typeof Info; bg: string; badgeVariant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "danger" }> = {
  INFO: { color: "text-blue-400", icon: Info, bg: "", badgeVariant: "default" },
  WARN: { color: "text-amber-400", icon: AlertTriangle, bg: "bg-amber-500/3", badgeVariant: "warning" },
  ERROR: { color: "text-red-400", icon: XCircle, bg: "bg-red-500/5 border-l-2 border-l-red-500/30", badgeVariant: "danger" },
  DEBUG: { color: "text-muted-foreground/40", icon: Bug, bg: "", badgeVariant: "secondary" },
};

const categoryConfig: Record<string, { icon: typeof Info; color: string; label: string }> = {
  signal:   { icon: Target,      color: "text-violet-400",  label: "Signal" },
  order:    { icon: ShoppingCart, color: "text-emerald-400", label: "Order" },
  orders:   { icon: ShoppingCart, color: "text-emerald-400", label: "Order" },
  position: { icon: Activity,    color: "text-cyan-400",    label: "Position" },
  risk:     { icon: ShieldAlert,  color: "text-amber-400",   label: "Risk" },
  trading:  { icon: Zap,         color: "text-violet-400",  label: "Trading" },
  data:     { icon: Database,    color: "text-cyan-400",    label: "Data" },
  engine:   { icon: Settings2,   color: "text-blue-400",    label: "Engine" },
  system:   { icon: Terminal,    color: "text-slate-400",   label: "System" },
  protocol: { icon: RadioTower,  color: "text-slate-400",   label: "Protocol" },
  sidecar:  { icon: Terminal,    color: "text-slate-400",   label: "Sidecar" },
};

export const LogsPage = memo(function LogsPage() {
  const { logs, filterLevel, filterCategory, autoScroll, setLogs, clearLogs, setAutoScroll } = useLogStore();
  const parentRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    // Defer setting 100 entries to next tick so the tab paints first and doesn't hang
    logsApi
      .get(undefined, undefined, 100)
      .then((entries) => {
        requestAnimationFrame(() => setLogs(entries));
      })
      .catch(console.error);
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

  // Category counts for the new trading categories
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
    // Defer scroll to avoid layout thrash in the same frame as a big log update
    const id = requestAnimationFrame(() => {
      if (parentRef.current) parentRef.current.scrollTop = parentRef.current.scrollHeight;
    });
    return () => cancelAnimationFrame(id);
  }, [filtered.length, autoScroll]);

  return (
    <div className="space-y-2.5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-tight flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-muted-foreground/50" />
            System Logs
          </h2>
          <p className="text-[9px] text-muted-foreground/40">Trading engine and system log viewer</p>
        </div>
        <div className="flex gap-1.5">
          <Button variant="outline" size="sm" onClick={() => setAutoScroll(!autoScroll)} className="h-7 text-[11px]">
            <ArrowDown className={cn("h-3 w-3 mr-1", autoScroll && "text-primary")} />
            Auto-scroll {autoScroll ? "ON" : "OFF"}
          </Button>
          <Button variant="outline" size="sm" onClick={async () => { await logsApi.clear(); clearLogs(); }} className="h-7 text-[11px]">
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
        <span className="w-px h-4 bg-border/40 mx-1" />
        {/* Trading category counts */}
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
        {/* Inline search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search logs…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-7 pl-7 pr-2.5 rounded-md border border-border/30 bg-muted/20 text-[11px] focus:outline-none focus:ring-1 focus:ring-ring w-48"
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
                  const catCfg = categoryConfig[l.category?.toLowerCase()] || { icon: Terminal, color: "text-muted-foreground/30", label: l.category || "—" };
                  const LevelIcon = cfg.icon;
                  const CatIcon = catCfg.icon;

                  return (
                    <div
                      key={`${l.timestamp}-${virtualRow.index}`}
                      className={cn(
                        "absolute left-0 top-0 flex items-center gap-2 px-3 border-b border-border/15 hover:bg-muted/20 w-full transition-colors stripe-row",
                        cfg.bg
                      )}
                      style={{ height: ROW_HEIGHT, transform: `translateY(${virtualRow.start}px)` }}
                    >
                      {/* Row number */}
                      <span className="text-muted-foreground/15 shrink-0 w-7 text-right tabular-nums text-[9px]">
                        {virtualRow.index + 1}
                      </span>

                      {/* Timestamp */}
                      <span className="text-muted-foreground/35 shrink-0 w-14 tabular-nums text-[9px]">
                        {formatTime(l.timestamp)}
                      </span>

                      {/* Level icon + label */}
                      <span className={cn("flex items-center gap-0.5 shrink-0 w-12", cfg.color)}>
                        <LevelIcon className="h-2.5 w-2.5" />
                        <span className="font-semibold text-[9px]">{l.level}</span>
                      </span>

                      {/* Category icon + label */}
                      <span className={cn("flex items-center gap-0.5 shrink-0 w-14", catCfg.color)}>
                        <CatIcon className="h-2.5 w-2.5" />
                        <span className="text-[9px] opacity-60">{catCfg.label}</span>
                      </span>

                      {/* Message */}
                      <span className="text-foreground/65 break-all flex-1 text-[10px] truncate">
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
