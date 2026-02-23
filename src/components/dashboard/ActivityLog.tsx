import { useRef, useEffect, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";
import { cn, formatTime } from "@/lib/utils";
import { Terminal } from "lucide-react";

const ROW_HEIGHT = 22;
const levelColor: Record<string, string> = {
  INFO: "text-blue-400",
  WARN: "text-amber-400",
  ERROR: "text-red-400",
  DEBUG: "text-muted-foreground/50",
};

export function ActivityLog() {
  const { logs, autoScroll } = useLogStore();
  const parentRef = useRef<HTMLDivElement>(null);
  const recentLogs = useMemo(() => logs.slice(-50), [logs]);

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

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5" /> Activity
        </CardTitle>
        <Badge variant="secondary" className="text-2xs">{logs.length}</Badge>
      </CardHeader>
      <CardContent>
        <div ref={parentRef} className="h-44 overflow-y-auto rounded-md bg-muted/50 border p-2.5 font-mono text-2xs">
          {recentLogs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8 text-xs">
              No activity yet. Start trading to see logs.
            </p>
          ) : (
            <div
              style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
              className="w-full"
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const log = recentLogs[virtualRow.index];
                return (
                  <div
                    key={`${log.timestamp}-${virtualRow.index}`}
                    className="absolute left-0 top-0 flex gap-2 w-full leading-relaxed"
                    style={{ height: ROW_HEIGHT, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    <span className="text-muted-foreground/40 shrink-0">{formatTime(log.timestamp)}</span>
                    <span className={cn("shrink-0 font-medium w-10", levelColor[log.level])}>{log.level}</span>
                    <span className="text-foreground/70 break-all">{log.message}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
