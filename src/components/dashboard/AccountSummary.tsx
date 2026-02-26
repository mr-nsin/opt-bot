import { Wallet, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { trading } from "@/lib/tauri-commands";
import { useEffect, useRef, useState } from "react";

const TAG_LABELS: Record<string, string> = {
  NetLiquidation: "Net Liquidation",
  TotalCashValue: "Total Cash",
  GrossPositionValue: "Gross Position Value",
  BuyingPower: "Buying Power",
  AvailableFunds: "Available Funds",
  ExcessLiquidity: "Excess Liquidity",
  MaintMarginReq: "Maint. Margin Req",
  InitialMarginReq: "Initial Margin Req",
  RealizedPnL: "Realized P&L",
  UnrealizedPnL: "Unrealized P&L",
  SettledCash: "Settled Cash",
  EquityWithLoanValue: "Equity w/ Loan",
};

// Primary tags shown prominently
const PRIMARY_TAGS = ["NetLiquidation", "BuyingPower", "AvailableFunds", "EquityWithLoanValue"];

// P&L related tags
const PNL_TAGS = ["RealizedPnL", "UnrealizedPnL"];

const TAG_ORDER = [
  "NetLiquidation",
  "TotalCashValue",
  "EquityWithLoanValue",
  "GrossPositionValue",
  "BuyingPower",
  "AvailableFunds",
  "ExcessLiquidity",
  "SettledCash",
  "MaintMarginReq",
  "InitialMarginReq",
  "RealizedPnL",
  "UnrealizedPnL",
];

export function AccountSummary() {
  const { accountMetrics, status, connectedToTws, setAccountMetrics } = useTradingStore();
  const [loading, setLoading] = useState(false);
  const pollTimeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (status !== "Running" && !connectedToTws) return;
    setLoading(true);
    pollTimeoutsRef.current = [];
    const parseAndSet = (m: Record<string, unknown> | null) => {
      if (!m || typeof m !== "object" || Object.keys(m).length === 0) return false;
      const parsed: Record<string, number> = {};
      for (const [k, v] of Object.entries(m)) {
        if (typeof v === "number" && !Number.isNaN(v)) parsed[k] = v;
      }
      if (Object.keys(parsed).length > 0) {
        setAccountMetrics(parsed);
        return true;
      }
      return false;
    };
    const fetchOnce = () =>
      trading.getAccountMetrics().then((m) => {
        if (m && typeof m === "object") return parseAndSet(m as Record<string, unknown>);
        return false;
      });
    fetchOnce().then((hadData) => {
      setLoading(false);
      if (hadData) return;
      pollTimeoutsRef.current.push(window.setTimeout(() => fetchOnce().then(() => {}), 600));
      pollTimeoutsRef.current.push(window.setTimeout(() => fetchOnce().then(() => {}), 1600));
    });
    return () => {
      pollTimeoutsRef.current.forEach((t) => window.clearTimeout(t));
      pollTimeoutsRef.current = [];
    };
  }, [status, connectedToTws, setAccountMetrics]);

  const entries = accountMetrics
    ? TAG_ORDER.filter((tag) => accountMetrics[tag] !== undefined).map((tag) => ({
        tag,
        label: TAG_LABELS[tag] ?? tag,
        value: Number(accountMetrics[tag]),
      }))
    : [];

  const primaryEntries = entries.filter((e) => PRIMARY_TAGS.includes(e.tag));
  const pnlEntries = entries.filter((e) => PNL_TAGS.includes(e.tag));
  const secondaryEntries = entries.filter(
    (e) => !PRIMARY_TAGS.includes(e.tag) && !PNL_TAGS.includes(e.tag)
  );

  return (
    <Card>
      <CardHeader className="py-2 flex flex-row items-center justify-between">
        <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
          <Wallet className="h-3 w-3 text-primary/60" />
          Account Summary
          <Badge variant="outline" className="text-[9px] font-normal h-4 px-1">IBKR</Badge>
        </CardTitle>
        <div className="flex items-center gap-2">
          {connectedToTws && (
            <Badge variant="success" className="text-2xs gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Connected
            </Badge>
          )}
          {loading && (
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground animate-spin" />
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {entries.length === 0 ? (
          loading ? (
            /* Skeleton loading state */
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-5 w-16" />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground py-4 text-center">
              Connect to TWS and start trading to see live account metrics (updates every 5s).
            </p>
          )
        ) : (
          <div className="space-y-2">
            {/* Primary metrics */}
            {primaryEntries.length > 0 && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-1.5">
                {primaryEntries.map(({ tag, label, value }) => (
                  <div key={tag} className="rounded-md bg-muted/20 border border-border/30 p-2">
                    <span className="text-[9px] text-muted-foreground/50 block mb-0.5">{label}</span>
                    <span className="font-mono font-bold tabular-nums text-xs">
                      {formatCurrency(value)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* P&L entries with color coding */}
            {pnlEntries.length > 0 && (
              <div className="grid grid-cols-2 gap-1.5">
                {pnlEntries.map(({ tag, label, value }) => (
                  <div key={tag} className="flex items-center gap-2 rounded-md bg-muted/20 border border-border/30 p-2">
                    {value >= 0 ? (
                      <TrendingUp className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5 text-red-500 shrink-0" />
                    )}
                    <div>
                      <span className="text-[9px] text-muted-foreground/50 block">{label}</span>
                      <span className={cn(
                        "font-mono font-bold tabular-nums text-xs",
                        pnlColor(value),
                        value > 0 ? "metric-profit" : value < 0 ? "metric-loss" : ""
                      )}>
                        {formatCurrency(value)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Secondary metrics - compact */}
            {secondaryEntries.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-3 gap-y-1.5 text-[10px] pt-1.5 border-t border-border/20">
                {secondaryEntries.map(({ tag, label, value }) => (
                  <div key={tag} className="flex flex-col">
                    <span className="text-muted-foreground/50 text-[9px]">{label}</span>
                    <span className="font-mono font-semibold tabular-nums text-[11px]">
                      {formatCurrency(value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
