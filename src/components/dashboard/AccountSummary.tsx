import { Wallet, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTradingStore } from "@/stores/tradingStore";
import { formatCurrency } from "@/lib/utils";
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

  // Load last snapshot when engine is running; short polling after Start Trading so we show IBKR data as soon as TWS responds
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
      // TWS may still be sending first account summary; poll a few times so we show data without waiting up to 5s
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
        label: TAG_LABELS[tag] ?? tag,
        value: Number(accountMetrics[tag]),
      }))
    : [];

  return (
    <Card>
      <CardHeader className="py-2.5 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Wallet className="h-4 w-4 text-primary" />
          Account Summary (IBKR)
        </CardTitle>
        {loading && (
          <RefreshCw className="h-3.5 w-3.5 text-muted-foreground animate-spin" />
        )}
      </CardHeader>
      <CardContent className="pt-0">
        {entries.length === 0 ? (
          <p className="text-xs text-muted-foreground py-4 text-center">
            Connect to TWS and start trading to see live account metrics (updates every 5s).
          </p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-3 text-xs">
            {entries.map(({ label, value }) => (
              <div key={label} className="flex flex-col gap-0.5">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-mono font-semibold tabular-nums">
                  {formatCurrency(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
