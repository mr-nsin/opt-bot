import { useRef, useEffect, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LogFilter } from "./LogFilter";
import { useLogStore } from "@/stores/logStore";
import { logs as logsApi } from "@/lib/tauri-commands";
import { cn, formatTime } from "@/lib/utils";
import { Trash2, ArrowDown } from "lucide-react";

const ROW_HEIGHT = 28;
const levelColor: Record<string, string> = { INFO: "text-blue-400", WARN: "text-amber-400", ERROR: "text-red-400", DEBUG: "text-muted-foreground/50" };
const levelBg: Record<string, string> = { ERROR: "bg-red-500/5", WARN: "bg-amber-500/5" };

export function LogsPage() {
  const { logs, filterLevel, filterCategory, autoScroll, setLogs, clearLogs, setAutoScroll } = useLogStore();
  const parentRef = useRef<HTMLDivElement>(null);

  useEffect(() => { logsApi.get(undefined, undefined, 500).then(setLogs).catch(console.error); }, [setLogs]);

  const filtered = useMemo(
    () =>
      logs.filter((l) => {
        if (filterLevel && l.level !== filterLevel) return false;
        if (filterCategory && l.category !== filterCategory) return false;
        return true;
      }),
    [logs, filterLevel, filterCategory]
  );

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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">System Logs</h2>
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

      <LogFilter />

      <Card>
        <CardHeader className="py-2.5">
          <CardTitle className="text-2xs text-muted-foreground">{filtered.length} of {logs.length} entries</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div ref={parentRef} className="h-[calc(100vh-280px)] overflow-y-auto font-mono text-2xs">
            {filtered.length === 0 ? (
              <p className="text-center text-xs text-muted-foreground py-16">No logs</p>
            ) : (
              <div
                style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
                className="w-full"
              >
                {virtualizer.getVirtualItems().map((virtualRow) => {
                  const l = filtered[virtualRow.index];
                  return (
                    <div
                      key={`${l.timestamp}-${virtualRow.index}`}
                      className={cn(
                        "absolute left-0 top-0 flex gap-3 px-4 border-b border-border/30 hover:bg-muted/30 w-full",
                        levelBg[l.level]
                      )}
                      style={{ height: ROW_HEIGHT, transform: `translateY(${virtualRow.start}px)` }}
                    >
                      <span className="text-muted-foreground/40 shrink-0 w-16 tabular-nums py-1">{formatTime(l.timestamp)}</span>
                      <span className={cn("shrink-0 w-10 font-medium py-1", levelColor[l.level])}>{l.level}</span>
                      <span className="text-muted-foreground shrink-0 w-16 py-1">{l.category}</span>
                      <span className="text-foreground/70 break-all py-1">{l.message}</span>
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
}
