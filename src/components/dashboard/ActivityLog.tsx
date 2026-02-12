import { useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLogStore } from "@/stores/logStore";
import { cn, formatTime } from "@/lib/utils";
import { Terminal } from "lucide-react";

export function ActivityLog() {
  const { logs, autoScroll } = useLogStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const recentLogs = logs.slice(-50);

  const levelColor: Record<string, string> = {
    INFO: "text-blue-400",
    WARN: "text-amber-400",
    ERROR: "text-red-400",
    DEBUG: "text-muted-foreground/50",
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5" /> Activity
        </CardTitle>
        <Badge variant="secondary" className="text-2xs">{logs.length}</Badge>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="h-44 overflow-y-auto rounded-md bg-muted/50 border p-2.5 font-mono text-2xs space-y-px">
          {recentLogs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8 text-xs">
              No activity yet. Start trading to see logs.
            </p>
          ) : (
            recentLogs.map((log, i) => (
              <div key={i} className="flex gap-2 leading-relaxed py-0.5">
                <span className="text-muted-foreground/40 shrink-0">{formatTime(log.timestamp)}</span>
                <span className={cn("shrink-0 font-medium w-10", levelColor[log.level])}>{log.level}</span>
                <span className="text-foreground/70 break-all">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
