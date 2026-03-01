import { memo } from "react";
import { useTradingStore } from "@/stores/tradingStore";

/** Compact market live indicator. Stock prices are shown in the Overview grid below Account Summary. */
export const MarketTicker = memo(function MarketTicker() {
  const connectedToTws = useTradingStore((s) => s.connectedToTws);

  return (
    <div className="h-8 bg-card/50 backdrop-blur-sm border-b border-border/15 flex items-center overflow-hidden shrink-0">
      <div className="flex items-center gap-1 px-3 h-full shrink-0">
        {connectedToTws ? (
          <>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 live-dot" />
            <span className="text-xs font-bold text-emerald-400 tracking-widest">MKT</span>
          </>
        ) : (
          <>
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
            <span className="text-xs font-bold text-muted-foreground/40 tracking-widest">MKT</span>
          </>
        )}
      </div>
    </div>
  );
});
