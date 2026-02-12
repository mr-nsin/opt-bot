import { useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LogFilter } from "./LogFilter";
import { useLogStore } from "@/stores/logStore";
import { logs as logsApi } from "@/lib/tauri-commands";
import { cn, formatTime } from "@/lib/utils";
import { Trash2, ArrowDown } from "lucide-react";

export function LogsPage() {
  const { logs, filterLevel, filterCategory, autoScroll, setLogs, clearLogs, setAutoScroll } = useLogStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { logsApi.get(undefined, undefined, 500).then(setLogs).catch(console.error); }, [setLogs]);
  useEffect(() => { if (autoScroll && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [logs, autoScroll]);

  const filtered = logs.filter((l) => {
    if (filterLevel && l.level !== filterLevel) return false;
    if (filterCategory && l.category !== filterCategory) return false;
    return true;
  });

  const levelColor: Record<string, string> = { INFO: "text-blue-400", WARN: "text-amber-400", ERROR: "text-red-400", DEBUG: "text-muted-foreground/50" };
  const levelBg: Record<string, string> = { ERROR: "bg-red-500/5", WARN: "bg-amber-500/5" };

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
          <div ref={scrollRef} className="h-[calc(100vh-280px)] overflow-y-auto font-mono text-2xs">
            {filtered.length === 0 ? (
              <p className="text-center text-xs text-muted-foreground py-16">No logs</p>
            ) : (
              filtered.map((l, i) => (
                <div key={i} className={cn("flex gap-3 px-4 py-1 border-b border-border/30 hover:bg-muted/30", levelBg[l.level])}>
                  <span className="text-muted-foreground/40 shrink-0 w-16 tabular-nums">{formatTime(l.timestamp)}</span>
                  <span className={cn("shrink-0 w-10 font-medium", levelColor[l.level])}>{l.level}</span>
                  <span className="text-muted-foreground shrink-0 w-16">{l.category}</span>
                  <span className="text-foreground/70 break-all">{l.message}</span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
