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
      <Card>
        <CardHeader>
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Controls
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          <Button
            onClick={handleStart}
            disabled={!canStart || isStarting}
            className="w-full h-10"
            variant="success"
            title={!tradingConfig ? "Load config first (open Dashboard or refresh)" : undefined}
          >
            {isStarting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Loading config & engine…</>
            ) : (
              <><Play className="h-4 w-4" /> Start Trading</>
            )}
          </Button>
          {startDurationSec != null && isRunning && (
            <p className="text-2xs text-muted-foreground text-center">
              Started in {startDurationSec}s
            </p>
          )}

          <Button
            onClick={handleStop}
            disabled={!isRunning || isStopping}
            className="w-full h-10"
            variant="outline"
          >
            {isStopping ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Stopping...</>
            ) : (
              <><Square className="h-4 w-4" /> Stop Trading</>
            )}
          </Button>

          <Button
            onClick={() => setShowEmergencyConfirm(true)}
            variant="destructive"
            className="w-full h-10"
          >
            <AlertTriangle className="h-4 w-4" /> Emergency Stop
          </Button>

          <div className="pt-2.5 mt-1 border-t">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Status</span>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "h-2 w-2 rounded-full",
                  isRunning ? "bg-emerald-500 live-dot" : isIdle ? "bg-muted-foreground/30" : "bg-amber-500"
                )} />
                <span className={cn(
                  "text-xs font-medium",
                  isRunning && "text-emerald-500",
                  isIdle && "text-muted-foreground",
                  typeof status === "object" && "text-red-500"
                )}>
                  {typeof status === "string" ? status : `Error: ${status.Error}`}
                </span>
              </div>
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-500 bg-red-500/10 rounded-md p-2.5 border border-red-500/20">
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
