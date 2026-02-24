import { useRef, useEffect, useMemo, memo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";
import { cn, formatTime } from "@/lib/utils";
import {
  Terminal,
  AlertTriangle,
  Info,
  Bug,
  Zap,
  ShoppingCart,
  Database,
  Settings2,
  XCircle,
} from "lucide-react";

const ROW_HEIGHT = 26;

const levelConfig: Record<string, { color: string; icon: typeof Info; bgClass?: string }> = {
  INFO: { color: "text-blue-400", icon: Info },
  WARN: { color: "text-amber-400", icon: AlertTriangle, bgClass: "bg-amber-500/3" },
  ERROR: { color: "text-red-400", icon: XCircle, bgClass: "bg-red-500/5" },
  DEBUG: { color: "text-muted-foreground/40", icon: Bug },
};

const categoryIcon: Record<string, typeof Info> = {
  trading: Zap,
  order: ShoppingCart,
  orders: ShoppingCart,
  data: Database,
  engine: Settings2,
  signal: Zap,
  system: Terminal,
};

export const ActivityLog = memo(function ActivityLog() {
  const logs = useLogStore((s) => s.logs);
  const autoScroll = useLogStore((s) => s.autoScroll);
  const parentRef = useRef<HTMLDivElement>(null);
  const recentLogs = useMemo(() => logs.slice(-60), [logs]);

  const virtualizer = useVirtualizer({
    count: recentLogs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
  });

  useEffect(() => {
    if (autoScroll && parentRef.current) {
      parentRef.current.scrollTop = parentRef.current.scrollHeight;
    }
  }, [recentLogs.length, autoScroll]);

  // Count errors/warnings for badge
  const errorCount = useMemo(
    () => recentLogs.filter((l) => l.level === "ERROR").length,
    [recentLogs]
  );
  const warnCount = useMemo(
    () => recentLogs.filter((l) => l.level === "WARN").length,
    [recentLogs]
  );

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5" /> Activity
        </CardTitle>
        <div className="flex items-center gap-1.5">
          {errorCount > 0 && (
            <Badge variant="danger" className="text-2xs px-1.5 py-0 gap-1">
              <XCircle className="h-2.5 w-2.5" />
              {errorCount}
            </Badge>
          )}
          {warnCount > 0 && (
            <Badge variant="warning" className="text-2xs px-1.5 py-0 gap-1">
              <AlertTriangle className="h-2.5 w-2.5" />
              {warnCount}
            </Badge>
          )}
          <Badge variant="secondary" className="text-2xs">{logs.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div
          ref={parentRef}
          className="h-48 overflow-y-auto rounded-lg bg-muted/30 border border-border/50 font-mono text-2xs"
        >
          {recentLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <Terminal className="h-6 w-6 text-muted-foreground/20 mb-2" />
              <p className="text-muted-foreground text-xs">
                No activity yet
              </p>
              <p className="text-muted-foreground/50 text-2xs mt-0.5">
                Start trading to see real-time logs
              </p>
            </div>
          ) : (
            <div
              style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
              className="w-full"
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const log = recentLogs[virtualRow.index];
                const levelCfg = levelConfig[log.level] || levelConfig.INFO;
                const CatIcon = categoryIcon[log.category?.toLowerCase()] || Terminal;
                const LevelIcon = levelCfg.icon;

                return (
                  <div
                    key={`${log.timestamp}-${virtualRow.index}`}
                    className={cn(
                      "absolute left-0 top-0 flex items-center gap-2 w-full px-2.5 leading-relaxed hover:bg-muted/40 transition-colors",
                      levelCfg.bgClass
                    )}
                    style={{
                      height: ROW_HEIGHT,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    {/* Timestamp */}
                    <span className="text-muted-foreground/30 shrink-0 tabular-nums w-14">
                      {formatTime(log.timestamp)}
                    </span>

                    {/* Level icon */}
                    <LevelIcon
                      className={cn("h-3 w-3 shrink-0", levelCfg.color)}
                    />

                    {/* Category icon */}
                    <CatIcon className="h-3 w-3 shrink-0 text-muted-foreground/30" />

                    {/* Level label */}
                    <span
                      className={cn(
                        "shrink-0 font-semibold w-9 text-2xs",
                        levelCfg.color
                      )}
                    >
                      {log.level}
                    </span>

                    {/* Message */}
                    <span className="text-foreground/70 truncate flex-1">
                      {log.message}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
