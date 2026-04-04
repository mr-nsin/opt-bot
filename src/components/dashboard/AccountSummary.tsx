import { Wallet, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useTradingStore } from "@/stores/tradingStore";
import { cn, formatCurrency, pnlColor } from "@/lib/utils";
import { trading } from "@/lib/tauri-commands";
import { useEffect, useState } from "react";

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

// Top grid: 4 cols × 2 rows — each column has (row1, row2) so Total Cash aligns under Net Liquidation
const TOP_GRID_ORDER: [string, string][] = [
  ["NetLiquidation", "TotalCashValue"],
  ["EquityWithLoanValue", "GrossPositionValue"],
  ["BuyingPower", "ExcessLiquidity"],
  ["AvailableFunds", "MaintMarginReq"],
];

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
  const accountMetrics = useTradingStore((s) => s.accountMetrics);
  const status = useTradingStore((s) => s.status);
  const connectedToTws = useTradingStore((s) => s.connectedToTws);
  const setAccountMetrics = useTradingStore((s) => s.setAccountMetrics);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (status !== "Running" && !connectedToTws) return;
    setLoading(true);
    trading
      .getAccountMetrics()
      .then((m) => {
        if (m && typeof m === "object" && Object.keys(m as object).length > 0) {
          const parsed: Record<string, number> = {};
          for (const [k, v] of Object.entries(m as Record<string, unknown>)) {
            if (typeof v === "number" && !Number.isNaN(v)) parsed[k] = v;
          }
          if (Object.keys(parsed).length > 0) setAccountMetrics(parsed);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [status, connectedToTws, setAccountMetrics]);

  const entries = accountMetrics
    ? TAG_ORDER.filter((tag) => accountMetrics[tag] !== undefined).map((tag) => ({
        tag,
        label: TAG_LABELS[tag] ?? tag,
        value: Number(accountMetrics[tag]),
      }))
    : [];

  const entryMap = Object.fromEntries(entries.map((e) => [e.tag, e]));
  const pnlEntries = entries.filter((e) => PNL_TAGS.includes(e.tag));
  const restTags = TAG_ORDER.filter(
    (tag) => !TOP_GRID_ORDER.flat().includes(tag) && !PNL_TAGS.includes(tag)
  );
  const restEntries = restTags.map((tag) => entryMap[tag]).filter(Boolean);

  return (
    <Card className="min-w-0 overflow-hidden h-full flex flex-col">
      <CardHeader className="py-2 flex flex-row items-center justify-between shrink-0">
        <CardTitle className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Wallet className="h-5 w-5 text-primary/80" />
          Account Summary
          <Badge variant="outline" className="text-xs font-medium h-5 px-1.5">IBKR</Badge>
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
      <CardContent className="pt-0 flex-1 flex flex-col min-h-0">
        {entries.length === 0 ? (
          loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-5 w-16" />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground/90 py-6 text-center">
              Connect to TWS and start trading to see live account metrics (updates every 5s).
            </p>
          )
        ) : (
          <div className="space-y-2 flex-1 flex flex-col min-h-0">
            {/* Top grid: 4 columns × 2 rows — Total Cash directly under Net Liquidation */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              {TOP_GRID_ORDER.map(([topTag, bottomTag]) => (
                <div key={`${topTag}-${bottomTag}`} className="flex flex-col gap-2 min-w-0">
                  {entryMap[topTag] && (
                    <div className="min-w-0 rounded-xl bg-muted/20 border border-border/15 p-3 overflow-hidden">
                      <span className="text-sm font-medium text-muted-foreground block mb-0.5 truncate">
                        {TAG_LABELS[topTag] ?? topTag}
                      </span>
                      <span className="font-mono font-bold tabular-nums text-lg block truncate" title={formatCurrency(entryMap[topTag].value)}>
                        {formatCurrency(entryMap[topTag].value)}
                      </span>
                    </div>
                  )}
                  {entryMap[bottomTag] && (
                    <div className="min-w-0 rounded-xl bg-muted/20 border border-border/15 p-3 overflow-hidden">
                      <span className="text-sm font-medium text-muted-foreground block mb-0.5 truncate">
                        {TAG_LABELS[bottomTag] ?? bottomTag}
                      </span>
                      <span className="font-mono font-bold tabular-nums text-lg block truncate" title={formatCurrency(entryMap[bottomTag].value)}>
                        {formatCurrency(entryMap[bottomTag].value)}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {pnlEntries.length > 0 && (
              <div className="grid grid-cols-2 gap-2">
                {pnlEntries.map(({ tag, label, value }) => (
                  <div key={tag} className="flex items-center gap-2 min-w-0 rounded-xl bg-muted/20 border border-border/15 p-3 overflow-hidden">
                    {value >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-emerald-500 shrink-0" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500 shrink-0" />
                    )}
                    <div className="min-w-0 flex-1 overflow-hidden">
                      <span className="text-sm font-medium text-muted-foreground block truncate">{label}</span>
                      <span className={cn(
                        "font-mono font-bold tabular-nums text-lg block truncate",
                        pnlColor(value),
                        value > 0 ? "metric-profit" : value < 0 ? "metric-loss" : ""
                      )} title={formatCurrency(value)}>
                        {formatCurrency(value)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {restEntries.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-3 gap-y-2 text-xs pt-3 border-t border-border/15">
                {restEntries.map(({ tag, label, value }) => (
                  <div key={tag} className="flex flex-col min-w-0 overflow-hidden">
                    <span className="text-muted-foreground text-sm font-medium truncate">{label}</span>
                    <span className="font-mono font-semibold tabular-nums text-sm truncate" title={formatCurrency(value)}>
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
