import { useState, useRef } from "react";
import { Play, Square, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useTradingEngine } from "@/hooks/useTradingEngine";
import { useConfigStore } from "@/stores/configStore";
import { cn } from "@/lib/utils";

export function TradingControls() {
  const { status, isRunning, isIdle, startTrading, stopTrading, emergencyStop } =
    useTradingEngine();
  const tradingConfig = useConfigStore((s) => s.tradingConfig);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDurationSec, setStartDurationSec] = useState<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const isStarting = status === "Starting";
  const isStopping = status === "Stopping";
  const canStart = isIdle && !!tradingConfig;

  const handleStart = async () => {
    setError(null);
    setStartDurationSec(null);
    startTimeRef.current = performance.now();
    try {
      await startTrading();
      if (startTimeRef.current != null) {
        const elapsed = (performance.now() - startTimeRef.current) / 1000;
        setStartDurationSec(Math.round(elapsed * 10) / 10);
        startTimeRef.current = null;
        setTimeout(() => setStartDurationSec(null), 8000);
      }
    } catch (err) {
      startTimeRef.current = null;
      setError(String(err));
    }
  };

  const handleStop = async () => {
    setError(null);
    setStartDurationSec(null);
    try { await stopTrading(); } catch (err) { setError(String(err)); }
  };

  const handleEmergencyStop = async () => {
    setShowEmergencyConfirm(false);
    try { await emergencyStop(); } catch (err) { setError(String(err)); }
  };

  return (
    <>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-1">
          <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Controls
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5 flex-1 flex flex-col">
          <Button
            onClick={handleStart}
            disabled={!canStart || isStarting}
            className="w-full h-7 text-[11px]"
            variant="success"
            title={!tradingConfig ? "Load config first (open Dashboard or refresh)" : undefined}
          >
            {isStarting ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Starting…</>
            ) : (
              <><Play className="h-3.5 w-3.5" /> Start Trading</>
            )}
          </Button>
          {startDurationSec != null && isRunning && (
            <p className="text-2xs text-muted-foreground/50 text-center">
              Started in {startDurationSec}s
            </p>
          )}

          <Button
            onClick={handleStop}
            disabled={!isRunning || isStopping}
            className="w-full h-7 text-[11px]"
            variant="outline"
          >
            {isStopping ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Stopping…</>
            ) : (
              <><Square className="h-3.5 w-3.5" /> Stop Trading</>
            )}
          </Button>

          <Button
            onClick={() => setShowEmergencyConfirm(true)}
            variant="destructive"
            className="w-full h-7 text-[11px]"
          >
            <AlertTriangle className="h-3.5 w-3.5" /> Emergency Stop
          </Button>

          <div className="flex-1" />

          <div className="pt-1.5 mt-auto border-t border-border/30">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground/50">Status</span>
              <div className="flex items-center gap-1.5">
                <span className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  isRunning ? "bg-emerald-500 live-dot" : isIdle ? "bg-muted-foreground/30" : "bg-amber-500"
                )} />
                <span className={cn(
                  "text-[10px] font-medium",
                  isRunning && "text-emerald-500",
                  isIdle && "text-muted-foreground/50",
                  typeof status === "object" && "text-red-500"
                )}>
                  {typeof status === "string" ? status : `Error: ${status.Error}`}
                </span>
              </div>
            </div>
          </div>

          {error && (
            <p className="text-[10px] text-red-500 bg-red-500/10 rounded-md p-2 border border-red-500/20">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showEmergencyConfirm}
        title="Emergency Stop"
        message="This will immediately kill the trading engine and close all connections. Any open orders may remain active on the broker side. Are you sure?"
        confirmLabel="Emergency Stop"
        variant="destructive"
        onConfirm={handleEmergencyStop}
        onCancel={() => setShowEmergencyConfirm(false)}
      />
    </>
  );
}
